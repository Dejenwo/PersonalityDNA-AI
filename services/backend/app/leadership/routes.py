"""Leadership development modules. Anyone can read them; signed-in users can track activities."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.api.v1.presenters import module_summary
from app.assessments.content import ContentBundle, LeadershipModule
from app.auth.deps import CurrentUser, optional_user
from app.database.models import LeadershipActivityProgress, User
from app.leadership.schemas import ActivityOut, LessonOut, ModuleList, ModuleListItem, ModuleOut

router = APIRouter(
    prefix="/api/v1/leadership", tags=["leadership"], responses={404: {"model": ErrorResponse}}
)
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
MaybeUser = Annotated[User | None, Depends(optional_user)]


def _done(db: Session, user: User | None) -> dict[tuple[str, str], datetime]:
    if user is None:
        return {}
    rows = db.scalars(select(LeadershipActivityProgress).where(LeadershipActivityProgress.user_id == user.id))
    return {(r.module_id, r.activity_id): r.completed_at for r in rows}


def _module(content: ContentBundle, module_id: str) -> LeadershipModule:
    m = content.leadership.data.module(module_id)
    if m is None:
        raise ApiError(404, "not_found", "Module not found.")
    return m


@router.get("/modules", response_model=ModuleList)
def list_modules(content: Content, db: Db, user: MaybeUser) -> ModuleList:
    done = _done(db, user)
    program = content.leadership.data
    return ModuleList(
        note=program.note,
        modules=[
            ModuleListItem(
                **module_summary(m).model_dump(),
                activities_total=len(m.activities),
                activities_done=sum(1 for a in m.activities if (m.id, a.id) in done),
            )
            for m in program.modules
        ],
    )


@router.get("/modules/{module_id}", response_model=ModuleOut)
def get_module(module_id: str, content: Content, db: Db, user: MaybeUser) -> ModuleOut:
    m = _module(content, module_id)
    done = _done(db, user)
    return ModuleOut(
        **module_summary(m).model_dump(),
        lessons=[LessonOut(title=x.title, text=x.text) for x in m.lessons],
        activities=[
            ActivityOut(id=a.id, title=a.title, steps=list(a.steps), completed_at=done.get((m.id, a.id)))
            for a in m.activities
        ],
        reflection=m.reflection,
    )


def _activity(content: ContentBundle, module_id: str, activity_id: str) -> None:
    m = _module(content, module_id)
    if not any(a.id == activity_id for a in m.activities):
        raise ApiError(404, "not_found", "Activity not found.")


@router.put(
    "/modules/{module_id}/activities/{activity_id}/done",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={401: {"model": ErrorResponse}},
)
def mark_done(module_id: str, activity_id: str, user: CurrentUser, db: Db, content: Content) -> Response:
    """Idempotent: marking an activity done twice keeps the first time."""
    _activity(content, module_id, activity_id)
    exists = db.scalar(
        select(LeadershipActivityProgress.id).where(
            LeadershipActivityProgress.user_id == user.id,
            LeadershipActivityProgress.module_id == module_id,
            LeadershipActivityProgress.activity_id == activity_id,
        )
    )
    if exists is None:
        db.add(
            LeadershipActivityProgress(
                id=uuid.uuid4(),
                user_id=user.id,
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
    "/modules/{module_id}/activities/{activity_id}/done",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={401: {"model": ErrorResponse}},
)
def mark_not_done(module_id: str, activity_id: str, user: CurrentUser, db: Db, content: Content) -> Response:
    _activity(content, module_id, activity_id)
    db.execute(
        delete(LeadershipActivityProgress).where(
            LeadershipActivityProgress.user_id == user.id,
            LeadershipActivityProgress.module_id == module_id,
            LeadershipActivityProgress.activity_id == activity_id,
        )
    )
    db.commit()
    return Response(status_code=204)
