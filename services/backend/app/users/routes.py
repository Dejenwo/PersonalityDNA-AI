"""Signed-in user endpoints: profile, claiming anonymous sessions, history, data export, deletion."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_content, get_db
from app.api.schemas import ErrorResponse, SessionOut
from app.api.v1 import presenters
from app.assessments import service as assessments
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.auth.routes import REFRESH_COOKIE, user_out
from app.auth.schemas import ClaimIn, DeleteAccountIn, HistoryItem, HistoryOut, UpdateMeIn, UserOut
from app.auth.service import AuthService
from app.coaching.service import CoachService
from app.database.models import AssessmentSession, CoachConversation, ConsentRecord

router = APIRouter(prefix="/api/v1", tags=["account"], responses={401: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]


@router.patch("/me", response_model=UserOut)
def update_me(body: UpdateMeIn, user: CurrentUser, db: Db) -> UserOut:
    data = body.model_dump(exclude_unset=True)
    if "display_name" in data:
        name = (data["display_name"] or "").strip()
        user.display_name = name or None
    if data.get("locale"):
        user.locale = data["locale"]
    db.commit()
    return user_out(user)


@router.post(
    "/me/assessment-sessions/claim", response_model=SessionOut, responses={404: {"model": ErrorResponse}}
)
def claim(body: ClaimIn, user: CurrentUser, db: Db, content: Content) -> SessionOut:
    assessments.claim_session(db, body.session_id, body.resume_token, user.id)
    session = assessments.get_authorized_session(db, body.session_id, None, user.id)
    return presenters.session_out(content, session)


def _user_sessions(db: Session, user_id: object) -> list[AssessmentSession]:
    return list(
        db.scalars(
            select(AssessmentSession)
            .where(AssessmentSession.user_id == user_id)
            .options(
                selectinload(AssessmentSession.responses),
                selectinload(AssessmentSession.version),
                selectinload(AssessmentSession.result),
            )
            .order_by(AssessmentSession.started_at.desc())
        )
    )


@router.get("/personality/history", response_model=HistoryOut, tags=["personality"])
def history(user: CurrentUser, db: Db, content: Content) -> HistoryOut:
    arch_names = {a.id: a.name for a in content.archetypes.data.archetypes}
    items = []
    for s in _user_sessions(db, user.id):
        inst = assessments.instrument_for(content, s).data
        primary = None
        if s.result is not None and not s.result.archetypes.get("weak_fit"):
            primary = arch_names.get(s.result.archetypes["ranking"][0]["id"])
        items.append(
            HistoryItem(
                session_id=s.id,
                instrument_id=inst.id,
                instrument_name=inst.name,
                status=s.status,
                started_at=s.started_at,
                completed_at=s.completed_at,
                result_id=s.result.id if s.result else None,
                primary_archetype=primary,
                answered=len(s.responses),
                total=len(inst.items),
            )
        )
    return HistoryOut(items=items)


@router.get("/privacy/export", tags=["privacy"])
def export(request: Request, user: CurrentUser, db: Db, content: Content) -> dict[str, Any]:
    """Everything stored about the signed-in user, as JSON (data portability)."""
    coach: CoachService = request.app.state.coach
    conversations = db.scalars(
        select(CoachConversation)
        .where(CoachConversation.user_id == user.id)
        .options(selectinload(CoachConversation.messages))
        .order_by(CoachConversation.created_at)
    ).all()
    consents = db.scalars(select(ConsentRecord).where(ConsentRecord.user_id == user.id)).all()
    sessions = []
    for s in _user_sessions(db, user.id):
        inst = assessments.instrument_for(content, s).data
        texts = {i.id: i.text for i in inst.items}
        sessions.append(
            {
                "session_id": str(s.id),
                "instrument": inst.id,
                "instrument_version": inst.version,
                "status": s.status,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "answers": [
                    {"item_id": r.item_id, "statement": texts.get(r.item_id), "value": r.value}
                    for r in sorted(s.responses, key=lambda r: r.item_id)
                ],
                "result": presenters.result_out(content, s.result).model_dump(mode="json")
                if s.result
                else None,
            }
        )
    return {
        "format": "personalitydna-export/1",
        "account": user_out(user).model_dump(mode="json"),
        "consents": [
            {
                "type": c.consent_type,
                "policy_version": c.policy_version,
                "granted": c.granted,
                "created_at": c.created_at.isoformat(),
            }
            for c in consents
        ],
        "assessments": sessions,
        "coach_conversations": [
            coach.conversation_out(c).model_dump(mode="json", exclude={"message_count"})
            for c in conversations
        ],
    }


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["privacy"],
    responses={403: {"model": ErrorResponse}},
)
def delete_account(body: DeleteAccountIn, request: Request, user: CurrentUser, db: Db) -> Response:
    """Permanently deletes the account and all assessments, answers and results linked to it."""
    auth: AuthService = request.app.state.auth
    auth.delete_account(db, user, body.password)
    response = Response(status_code=204)
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return response
