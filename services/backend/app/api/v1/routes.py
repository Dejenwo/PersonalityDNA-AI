import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import (
    AssessmentDetail,
    AssessmentList,
    CreateSessionIn,
    CreateSessionOut,
    ErrorResponse,
    ResultOut,
    SaveAnswersIn,
    SaveAnswersOut,
    SessionOut,
)
from app.api.v1 import presenters
from app.assessments import service
from app.assessments.content import ContentBundle
from app.auth.deps import OptionalUser
from app.database.models import User


def _uid(user: User | None) -> uuid.UUID | None:
    return user.id if user else None


router = APIRouter(prefix="/api/v1", responses={422: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})

Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
SessionToken = Annotated[
    str | None, Header(alias="X-Session-Token", description="Resume token for the session")
]


@router.get("/assessments", response_model=AssessmentList, tags=["assessments"])
def list_assessments(content: Content) -> AssessmentList:
    latest = {}
    for key in sorted(content.instruments):
        iid = key.split("@")[0]
        latest[iid] = service.latest_version(content, iid).data
    items = sorted(
        (presenters.summary(i) for i in latest.values()),
        key=lambda s: (s.family != "big_five", s.item_count, s.id),
    )
    return AssessmentList(items=items)


@router.get("/assessments/{instrument_id}", response_model=AssessmentDetail, tags=["assessments"])
def get_assessment(instrument_id: str, content: Content) -> AssessmentDetail:
    return presenters.detail(service.latest_version(content, instrument_id).data)


@router.post(
    "/assessment-sessions",
    response_model=CreateSessionOut,
    status_code=status.HTTP_201_CREATED,
    tags=["assessment-sessions"],
    responses={409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def create_session(
    body: CreateSessionIn, request: Request, db: Db, content: Content, user: OptionalUser
) -> CreateSessionOut:
    if not request.app.state.session_limiter.allow(client_ip(request)):
        raise ApiError(429, "rate_limited", "Too many new assessments. Please wait a minute and try again.")
    session, token = service.create_session(
        db,
        content,
        instrument_id=body.instrument_id,
        version=body.version,
        locale=body.locale,
        accepted=body.consent.accepted,
        age_confirmed=body.consent.age_confirmed_18_plus,
        policy_version=body.consent.policy_version,
        user_id=user.id if user else None,
    )
    return CreateSessionOut(session=presenters.session_out(content, session), resume_token=token)


@router.get("/assessment-sessions/{session_id}", response_model=SessionOut, tags=["assessment-sessions"])
def get_session(
    session_id: uuid.UUID, db: Db, content: Content, user: OptionalUser, token: SessionToken = None
) -> SessionOut:
    return presenters.session_out(content, service.get_authorized_session(db, session_id, token, _uid(user)))


@router.put(
    "/assessment-sessions/{session_id}/answers",
    response_model=SaveAnswersOut,
    tags=["assessment-sessions"],
    responses={409: {"model": ErrorResponse}},
)
def save_answers(
    session_id: uuid.UUID,
    body: SaveAnswersIn,
    db: Db,
    content: Content,
    user: OptionalUser,
    token: SessionToken = None,
) -> SaveAnswersOut:
    session = service.get_authorized_session(db, session_id, token, _uid(user))
    saved = service.save_answers(db, content, session, ((a.item_id, a.value) for a in body.answers))
    total = len(service.instrument_for(content, session).data.items)
    return SaveAnswersOut(saved=saved, progress=presenters.progress(len(session.responses), total))


@router.post(
    "/assessment-sessions/{session_id}/complete",
    response_model=ResultOut,
    tags=["assessment-sessions"],
    responses={409: {"model": ErrorResponse}},
)
def complete(
    session_id: uuid.UUID, db: Db, content: Content, user: OptionalUser, token: SessionToken = None
) -> ResultOut:
    session = service.get_authorized_session(db, session_id, token, _uid(user))
    result = service.complete_session(db, content, session)
    return presenters.result_out(content, service.get_authorized_result(db, result.id, token, _uid(user)))


@router.get("/results/{result_id}", response_model=ResultOut, tags=["results"])
def get_result(
    result_id: uuid.UUID, db: Db, content: Content, user: OptionalUser, token: SessionToken = None
) -> ResultOut:
    return presenters.result_out(content, service.get_authorized_result(db, result_id, token, _uid(user)))
