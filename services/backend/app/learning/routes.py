"""Learning tracks (leadership, emotional awareness). Anyone can read them; signed-in users can track
which activities they have done. Progress stores content ids only, never free text."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import ColumnElement, and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.api.v1.presenters import module_summary
from app.assessments.content import ContentBundle, LearningModule, LearningTrack
from app.auth.deps import CurrentUser, optional_user
from app.database.models import LearningActivityProgress, User
from app.learning.schemas import ActivityOut, LessonOut, ModuleList, ModuleListItem, ModuleOut

router = APIRouter(prefix="/api/v1/learning", tags=["learning"], responses={404: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
MaybeUser = Annotated[User | None, Depends(optional_user)]


def _track(content: ContentBundle, track_id: str) -> LearningTrack:
    t = content.track(track_id)
    if t is None:
        raise ApiError(404, "not_found", "Learning track not found.")
    return t


def _module(content: ContentBundle, track_id: str, module_id: str) -> LearningModule:
    m = _track(content, track_id).module(module_id)
    if m is None:
        raise ApiError(404, "not_found", "Module not found.")
    return m


def _done(db: Session, user: User | None, track_id: str) -> dict[tuple[str, str], datetime]:
    if user is None:
        return {}
    rows = db.scalars(
        select(LearningActivityProgress).where(
            LearningActivityProgress.user_id == user.id, LearningActivityProgress.track == track_id
        )
    )
    return {(r.module_id, r.activity_id): r.completed_at for r in rows}


@router.get("/{track_id}/modules", response_model=ModuleList)
def list_modules(track_id: str, content: Content, db: Db, user: MaybeUser) -> ModuleList:
    track = _track(content, track_id)
    done = _done(db, user, track_id)
    return ModuleList(
        track=track_id,
        title=track.title,
        note=track.note,
        support_note=track.support_note,
        modules=[
            ModuleListItem(
                **module_summary(m).model_dump(),
                activities_total=len(m.activities),
                activities_done=sum(1 for a in m.activities if (m.id, a.id) in done),
            )
            for m in track.modules
        ],
    )


@router.get("/{track_id}/modules/{module_id}", response_model=ModuleOut)
def get_module(track_id: str, module_id: str, content: Content, db: Db, user: MaybeUser) -> ModuleOut:
    m = _module(content, track_id, module_id)
    track = _track(content, track_id)
    done = _done(db, user, track_id)
    return ModuleOut(
        **module_summary(m).model_dump(),
        track=track_id,
        track_title=track.title,
        support_note=track.support_note,
        lessons=[LessonOut(title=x.title, text=x.text) for x in m.lessons],
        activities=[
            ActivityOut(id=a.id, title=a.title, steps=list(a.steps), completed_at=done.get((m.id, a.id)))
            for a in m.activities
        ],
        reflection=m.reflection,
    )


def _activity(content: ContentBundle, track_id: str, module_id: str, activity_id: str) -> None:
    m = _module(content, track_id, module_id)
    if not any(a.id == activity_id for a in m.activities):
        raise ApiError(404, "not_found", "Activity not found.")


def _match(user: User, track_id: str, module_id: str, activity_id: str) -> ColumnElement[bool]:
    return and_(
        LearningActivityProgress.user_id == user.id,
        LearningActivityProgress.track == track_id,
        LearningActivityProgress.module_id == module_id,
        LearningActivityProgress.activity_id == activity_id,
    )


DONE_PATH = "/{track_id}/modules/{module_id}/activities/{activity_id}/done"


@router.put(
    DONE_PATH,
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={401: {"model": ErrorResponse}},
)
def mark_done(
    track_id: str, module_id: str, activity_id: str, user: CurrentUser, db: Db, content: Content
) -> Response:
    """Idempotent: marking an activity done twice keeps the first time."""
    _activity(content, track_id, module_id, activity_id)
    match = _match(user, track_id, module_id, activity_id)
    exists = db.scalar(select(LearningActivityProgress.id).where(match))
    if exists is None:
        db.add(
            LearningActivityProgress(
                id=uuid.uuid4(),
                user_id=user.id,
                track=track_id,
                module_id=module_id,
                activity_id=activity_id,
                completed_at=datetime.now(UTC),
            )
        )
        try:
            db.commit()
        except IntegrityError:  # a concurrent request got there first
            db.rollback()
    return Response(status_code=204)


@router.delete(
    DONE_PATH,
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={401: {"model": ErrorResponse}},
)
def mark_not_done(
    track_id: str, module_id: str, activity_id: str, user: CurrentUser, db: Db, content: Content
) -> Response:
    _activity(content, track_id, module_id, activity_id)
    db.execute(delete(LearningActivityProgress).where(_match(user, track_id, module_id, activity_id)))
    db.commit()
    return Response(status_code=204)
