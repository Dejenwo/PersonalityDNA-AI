from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser
from app.auth.schemas import (
    AuthOut,
    EmailIn,
    LoginIn,
    MessageOut,
    OutboxItem,
    OutboxOut,
    RefreshIn,
    RegisterIn,
    ResetConfirmIn,
    TokenIn,
    UserOut,
)
from app.auth.service import AuthService, normalize_email
from app.database.models import User
from app.notifications.email import EmailSender, OutboxEmailSender, OutgoingEmail

router = APIRouter(prefix="/api/v1/auth", tags=["auth"], responses={422: {"model": ErrorResponse}})
dev_router = APIRouter(prefix="/api/v1/dev", tags=["development"])

Db = Annotated[Session, Depends(get_db)]
REFRESH_COOKIE = "pdna_refresh"
CSRF_HEADER = "X-PDNA-CSRF"
ACCEPTED = "If the details are valid, we've sent an email with next steps."


def _service(request: Request) -> AuthService:
    svc: AuthService = request.app.state.auth
    return svc


def _send(background: BackgroundTasks, request: Request, emails: list[OutgoingEmail]) -> None:
    sender: EmailSender = request.app.state.email
    for e in emails:
        background.add_task(sender.send, e)


def _limit(request: Request, *keys: str) -> None:
    limiter = request.app.state.auth_limiter
    if not all(limiter.allow(k) for k in keys):
        raise ApiError(429, "rate_limited", "Too many attempts. Please wait a few minutes and try again.")


def user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        locale=u.locale,
        email_verified=u.email_verified_at is not None,
        created_at=u.created_at,
    )


def _set_cookie(request: Request, response: Response, token: str) -> None:
    s = request.app.state.settings
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=s.refresh_token_days * 86400,
        httponly=True,
        secure=s.refresh_cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
        domain=s.refresh_cookie_domain,
    )


def _clear_cookie(request: Request, response: Response) -> None:
    s = request.app.state.settings
    response.delete_cookie(
        REFRESH_COOKIE,
        path="/api/v1/auth",
        domain=s.refresh_cookie_domain,
        secure=s.refresh_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _auth_response(
    request: Request, response: Response, db: Session, user: User, refresh: str, mobile: bool
) -> AuthOut:
    access, exp = request.app.state.access_tokens.issue(user.id)
    if mobile:
        return AuthOut(access_token=access, expires_at=exp, user=user_out(user), refresh_token=refresh)
    _set_cookie(request, response, refresh)
    return AuthOut(access_token=access, expires_at=exp, user=user_out(user))


@router.post(
    "/register",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def register(body: RegisterIn, request: Request, background: BackgroundTasks, db: Db) -> MessageOut:
    _limit(request, f"register:ip:{client_ip(request)}", f"register:email:{normalize_email(body.email)}")
    emails = _service(request).register(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        accepted_terms=body.accepted_terms,
        age_confirmed=body.age_confirmed_18_plus,
        policy_version=body.policy_version,
    )
    _send(background, request, emails)
    return MessageOut(message="Check your email to confirm your account.")


@router.post("/verify-email", response_model=UserOut, responses={400: {"model": ErrorResponse}})
def verify_email(body: TokenIn, request: Request, db: Db) -> UserOut:
    return user_out(_service(request).verify_email(db, body.token))


@router.post("/resend-verification", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
def resend_verification(body: EmailIn, request: Request, background: BackgroundTasks, db: Db) -> MessageOut:
    _limit(request, f"resend:ip:{client_ip(request)}", f"resend:email:{normalize_email(body.email)}")
    _send(background, request, _service(request).resend_verification(db, body.email))
    return MessageOut(message=ACCEPTED)


@router.post(
    "/login",
    response_model=AuthOut,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def login(body: LoginIn, request: Request, response: Response, db: Db) -> AuthOut:
    _limit(request, f"login:ip:{client_ip(request)}", f"login:email:{normalize_email(body.email)}")
    svc = _service(request)
    user = svc.authenticate(db, body.email, body.password)
    return _auth_response(request, response, db, user, svc.issue_refresh(db, user), body.client == "mobile")


@router.post("/refresh", response_model=AuthOut, responses={401: {"model": ErrorResponse}})
def refresh(
    request: Request,
    response: Response,
    db: Db,
    body: RefreshIn | None = None,
    cookie: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
    csrf: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
) -> AuthOut:
    mobile = body is not None and body.refresh_token is not None
    if not mobile and csrf != "1":
        # Cookie-based refresh must come from our own scripts (custom header forces a CORS preflight).
        raise ApiError(403, "csrf_required", "Missing request header.")
    raw = body.refresh_token if mobile and body else cookie
    try:
        user, new_refresh = _service(request).rotate_refresh(db, raw)
    except ApiError:
        if not mobile:
            _clear_cookie(request, response)
        raise
    return _auth_response(request, response, db, user, new_refresh, mobile)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(
    request: Request,
    db: Db,
    body: RefreshIn | None = None,
    cookie: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    _service(request).revoke_refresh(db, (body.refresh_token if body else None) or cookie)
    response = Response(status_code=204)
    _clear_cookie(request, response)
    return response


@router.post("/password-reset/request", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
def request_reset(body: EmailIn, request: Request, background: BackgroundTasks, db: Db) -> MessageOut:
    _limit(request, f"reset:ip:{client_ip(request)}", f"reset:email:{normalize_email(body.email)}")
    _send(background, request, _service(request).request_reset(db, body.email))
    return MessageOut(message=ACCEPTED)


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={400: {"model": ErrorResponse}},
)
def confirm_reset(body: ResetConfirmIn, request: Request, db: Db) -> Response:
    _service(request).reset_password(db, body.token, body.password)
    response = Response(status_code=204)
    _clear_cookie(request, response)
    return response


@router.get("/me", response_model=UserOut, responses={401: {"model": ErrorResponse}})
def auth_me(user: CurrentUser) -> UserOut:
    return user_out(user)


@dev_router.get("/outbox", response_model=OutboxOut)
def outbox(request: Request, to: str | None = None) -> OutboxOut:
    """Development only: emails 'sent' by the in-memory outbox. Disabled unless explicitly enabled."""
    sender = request.app.state.email
    if not isinstance(sender, OutboxEmailSender):
        raise ApiError(404, "not_found", "Not found.")
    items = [
        OutboxItem(to=m.to, subject=m.subject, text=m.text, kind=m.kind, sent_at=m.sent_at)
        for m in sender.messages(to)
    ]
    return OutboxOut(items=items)
