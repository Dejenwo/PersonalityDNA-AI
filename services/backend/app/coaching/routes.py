"""AI coach endpoints. Signed-in, verified users only; every conversation is scoped to its owner."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.coaching.schemas import (
    CoachStatus,
    ConversationList,
    ConversationOut,
    CreateConversationIn,
    SendMessageIn,
)
from app.coaching.service import CoachService
from app.database.models import User

router = APIRouter(prefix="/api/v1/coach", tags=["coach"], responses={401: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]


def get_coach(request: Request) -> CoachService:
    coach: CoachService = request.app.state.coach
    return coach


Coach = Annotated[CoachService, Depends(get_coach)]


def verified_user(user: CurrentUser, coach: Coach) -> User:
    coach.require_enabled()
    if user.email_verified_at is None:
        raise ApiError(403, "email_not_verified", "Please verify your email address to use the coach.")
    return user


VerifiedUser = Annotated[User, Depends(verified_user)]


@router.get("/status", response_model=CoachStatus)
def coach_status(user: CurrentUser, coach: Coach, db: Db) -> CoachStatus:
    return coach.status(db, user)


@router.get("/conversations", response_model=ConversationList, responses={403: {"model": ErrorResponse}})
def list_conversations(user: VerifiedUser, coach: Coach, db: Db) -> ConversationList:
    return ConversationList(items=coach.list_conversations(db, user.id))


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_conversation(
    body: CreateConversationIn, user: VerifiedUser, coach: Coach, db: Db
) -> ConversationOut:
    conv = coach.create_conversation(db, user, body)
    return coach.conversation_out(conv)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_conversation(conversation_id: uuid.UUID, user: VerifiedUser, coach: Coach, db: Db) -> ConversationOut:
    return coach.conversation_out(coach.get_conversation(db, user.id, conversation_id))


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def delete_conversation(conversation_id: uuid.UUID, user: VerifiedUser, coach: Coach, db: Db) -> Response:
    coach.delete_conversation(db, user.id, conversation_id)
    return Response(status_code=204)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Server-sent events: start, delta, retract, done or error.",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageIn,
    user: VerifiedUser,
    coach: Coach,
    db: Db,
    content: Content,
) -> StreamingResponse:
    conv = coach.get_conversation(db, user.id, conversation_id)
    events = coach.start_turn(db, content, conv, body.content)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
