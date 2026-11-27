"""Notification centre and preferences for the signed-in person."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser
from app.database.models import Notification
from app.notifications.service import KINDS, Kind, NotificationService

router = APIRouter(
    prefix="/api/v1/notifications", tags=["notifications"], responses={401: {"model": ErrorResponse}}
)
Db = Annotated[Session, Depends(get_db)]


def get_notifications(request: Request) -> NotificationService:
    svc: NotificationService = request.app.state.notifications
    return svc


Svc = Annotated[NotificationService, Depends(get_notifications)]


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    link: str | None
    created_at: datetime
    read: bool


class NotificationList(BaseModel):
    notifications: list[NotificationOut]
    unread: int
    next_before: datetime | None


class PreferenceOut(BaseModel):
    kind: Kind
    label: str
    description: str
    in_app: bool
    email: bool
    required: bool


class PreferenceIn(BaseModel):
    kind: Kind
    in_app: bool
    email: bool


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        kind=n.kind,
        title=n.title,
        body=n.body,
        link=n.link,
        created_at=_aware(n.created_at),
        read=n.read_at is not None,
    )


@router.get("", response_model=NotificationList)
def list_notifications(
    user: CurrentUser, db: Db, svc: Svc, before: datetime | None = None
) -> NotificationList:
    rows, unread = svc.list(db, user.id, before)
    return NotificationList(
        notifications=[_out(n) for n in rows],
        unread=unread,
        next_before=_aware(rows[-1].created_at) if len(rows) == 30 else None,
    )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def read_all(user: CurrentUser, db: Db, svc: Svc) -> Response:
    svc.mark_read(db, user.id, None)
    return Response(status_code=204)


@router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={404: {"model": ErrorResponse}},
)
def read_one(notification_id: uuid.UUID, user: CurrentUser, db: Db, svc: Svc) -> Response:
    svc.mark_read(db, user.id, notification_id)
    return Response(status_code=204)


def _prefs(db: Session, svc: NotificationService, user_id: uuid.UUID) -> list[PreferenceOut]:
    saved = svc.preferences(db, user_id)
    return [
        PreferenceOut(
            kind=kind,
            label=info.label,
            description=info.description,
            in_app=saved[kind][0],
            email=saved[kind][1],
            required=info.required,
        )
        for kind, info in KINDS.items()
    ]


@router.get("/preferences", response_model=list[PreferenceOut])
def preferences(user: CurrentUser, db: Db, svc: Svc) -> list[PreferenceOut]:
    return _prefs(db, svc, user.id)


@router.put("/preferences", response_model=list[PreferenceOut], responses={409: {"model": ErrorResponse}})
def set_preference(body: PreferenceIn, user: CurrentUser, db: Db, svc: Svc) -> list[PreferenceOut]:
    svc.set_preference(db, user.id, body.kind, body.in_app, body.email)
    return _prefs(db, svc, user.id)
