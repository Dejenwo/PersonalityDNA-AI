"""Personal growth academy: development programmes anyone can read, and enrolment, daily progress and weekly
self-evaluation for signed-in users. Progress holds day numbers and 1 to 5 ratings only, never free text."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle, GrowthAcademy, GrowthProgram
from app.auth.deps import CurrentUser, optional_user
from app.database.models import GrowthCheckIn, GrowthDayProgress, GrowthEnrollment, User
from app.growth.plan import PlanDay, next_day, plan_days
from app.growth.schemas import (
    CheckInIn,
    DayOut,
    EnrollmentOut,
    PracticeOut,
    ProgramList,
    ProgramOut,
    ProgramSummary,
    WeekOut,
)

router = APIRouter(prefix="/api/v1/growth", tags=["growth"], responses={404: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
MaybeUser = Annotated[User | None, Depends(optional_user)]
AUTH: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}
FREE_PROGRAM_DAYS = 7


def _program(content: ContentBundle, program_id: str) -> GrowthProgram:
    p = content.growth.data.program(program_id)
    if p is None:
        raise ApiError(404, "not_found", "Programme not found.")
    return p


def _enrollment(db: Session, user: User | None, program_id: str) -> GrowthEnrollment | None:
    if user is None:
        return None
    return db.scalar(
        select(GrowthEnrollment).where(
            GrowthEnrollment.user_id == user.id, GrowthEnrollment.program_id == program_id
        )
    )


def _required_enrollment(db: Session, user: User, program_id: str) -> GrowthEnrollment:
    e = _enrollment(db, user, program_id)
    if e is None:
        raise ApiError(409, "not_enrolled", "Start this programme first.")
    return e


def _days_done(db: Session, e: GrowthEnrollment | None) -> dict[int, datetime]:
    if e is None:
        return {}
    rows = db.scalars(select(GrowthDayProgress).where(GrowthDayProgress.enrollment_id == e.id))
    return {r.day: r.completed_at for r in rows}


def _summary(
    academy: GrowthAcademy, p: GrowthProgram, e: GrowthEnrollment | None, done: set[int]
) -> ProgramSummary:
    topics = list(dict.fromkeys(academy.week(w).topic for w in p.weeks))
    return ProgramSummary(
        id=p.id,
        title=p.title,
        days=p.days,
        kind="challenge" if p.days == 7 else "program",
        summary=p.summary,
        objectives=list(p.objectives),
        topics=topics,
        enrollment=None
        if e is None
        else EnrollmentOut(
            started_at=e.started_at,
            completed_at=e.completed_at,
            days_done=len(done),
            next_day=next_day(p.days, done),
        ),
    )


def _detail(db: Session, academy: GrowthAcademy, p: GrowthProgram, e: GrowthEnrollment | None) -> ProgramOut:
    done = _days_done(db, e)
    ratings: dict[int, int] = {}
    if e is not None:
        ratings = {
            c.week: c.rating
            for c in db.scalars(select(GrowthCheckIn).where(GrowthCheckIn.enrollment_id == e.id))
        }
    days = plan_days(academy, p)

    def day_out(d: PlanDay) -> DayOut:
        return DayOut(day=d.day, kind=d.kind, text=d.text, completed_at=done.get(d.day))

    weeks = []
    for number, week_id in enumerate(p.weeks, start=1):
        w = academy.week(week_id)
        weeks.append(
            WeekOut(
                number=number,
                topic=w.topic,
                title=w.title,
                objective=w.objective,
                lesson_title=w.lesson.title,
                practice=PracticeOut(title=w.practice.title, steps=list(w.practice.steps)),
                self_evaluation=w.self_evaluation,
                reflection=w.reflection,
                rating=ratings.get(number),
                days=[day_out(d) for d in days if d.week == number],
            )
        )
    return ProgramOut(
        **_summary(academy, p, e, set(done)).model_dump(),
        note=academy.note,
        self_evaluation_scale=list(academy.self_evaluation_scale),
        weeks=weeks,
        review_days=[day_out(d) for d in days if d.week is None],
    )


@router.get("/programs", response_model=ProgramList)
def list_programs(content: Content, db: Db, user: MaybeUser) -> ProgramList:
    academy = content.growth.data
    out = []
    for p in academy.programs:
        e = _enrollment(db, user, p.id)
        out.append(_summary(academy, p, e, set(_days_done(db, e))))
    return ProgramList(note=academy.note, programs=out)


@router.get("/programs/{program_id}", response_model=ProgramOut)
def get_program(program_id: str, content: Content, db: Db, user: MaybeUser) -> ProgramOut:
    p = _program(content, program_id)
    return _detail(db, content.growth.data, p, _enrollment(db, user, program_id))


@router.post("/programs/{program_id}/enrollment", response_model=ProgramOut, responses=AUTH)
def start_program(
    program_id: str, request: Request, user: CurrentUser, db: Db, content: Content
) -> ProgramOut:
    """Starts the programme, or restarts it from day 1 (clearing progress and self-evaluations).
    Seven-day challenges are free; longer programmes are part of Premium once billing is enforced."""
    p = _program(content, program_id)
    if p.days > FREE_PROGRAM_DAYS:
        request.app.state.entitlements.require(db, user.id, "growth_programs")
    e = _enrollment(db, user, program_id)
    if e is not None:
        db.delete(e)
        db.flush()
    e = GrowthEnrollment(
        id=uuid.uuid4(), user_id=user.id, program_id=program_id, started_at=datetime.now(UTC)
    )
    db.add(e)
    try:
        db.commit()
    except IntegrityError:  # a concurrent start won
        db.rollback()
        e = _required_enrollment(db, user, program_id)
    return _detail(db, content.growth.data, p, e)


@router.delete(
    "/programs/{program_id}/enrollment",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=AUTH,
)
def leave_program(program_id: str, user: CurrentUser, db: Db, content: Content) -> Response:
    """Leaves the programme and deletes its progress and self-evaluations."""
    _program(content, program_id)
    db.execute(
        delete(GrowthEnrollment).where(
            GrowthEnrollment.user_id == user.id, GrowthEnrollment.program_id == program_id
        )
    )
    db.commit()
    return Response(status_code=204)


def _sync_completed(db: Session, e: GrowthEnrollment, total: int) -> None:
    done = len(_days_done(db, e))
    if done >= total and e.completed_at is None:
        e.completed_at = datetime.now(UTC)
    elif done < total:
        e.completed_at = None


def _check_day(p: GrowthProgram, day: int) -> None:
    if not 1 <= day <= p.days:
        raise ApiError(404, "not_found", "Day not found.")


@router.put(
    "/programs/{program_id}/days/{day}/done",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=AUTH,
)
def mark_day_done(program_id: str, day: int, user: CurrentUser, db: Db, content: Content) -> Response:
    """Idempotent: marking a day done twice keeps the first time."""
    p = _program(content, program_id)
    _check_day(p, day)
    e = _required_enrollment(db, user, program_id)
    exists = db.scalar(
        select(GrowthDayProgress.id).where(
            GrowthDayProgress.enrollment_id == e.id, GrowthDayProgress.day == day
        )
    )
    if exists is None:
        db.add(
            GrowthDayProgress(id=uuid.uuid4(), enrollment_id=e.id, day=day, completed_at=datetime.now(UTC))
        )
        try:
            db.flush()
        except IntegrityError:  # a concurrent request got there first
            db.rollback()
            e = _required_enrollment(db, user, program_id)
    _sync_completed(db, e, p.days)
    db.commit()
    return Response(status_code=204)


@router.delete(
    "/programs/{program_id}/days/{day}/done",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=AUTH,
)
def mark_day_not_done(program_id: str, day: int, user: CurrentUser, db: Db, content: Content) -> Response:
    p = _program(content, program_id)
    _check_day(p, day)
    e = _required_enrollment(db, user, program_id)
    db.execute(
        delete(GrowthDayProgress).where(GrowthDayProgress.enrollment_id == e.id, GrowthDayProgress.day == day)
    )
    _sync_completed(db, e, p.days)
    db.commit()
    return Response(status_code=204)


def _check_week(p: GrowthProgram, week: int) -> None:
    if not 1 <= week <= len(p.weeks):
        raise ApiError(404, "not_found", "Week not found.")


@router.put(
    "/programs/{program_id}/weeks/{week}/check-in",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**AUTH, 422: {"model": ErrorResponse}},
)
def set_check_in(
    program_id: str, week: int, body: CheckInIn, user: CurrentUser, db: Db, content: Content
) -> Response:
    """Saves or replaces the week's self-evaluation (1 to 5)."""
    p = _program(content, program_id)
    _check_week(p, week)
    e = _required_enrollment(db, user, program_id)
    c = db.scalar(
        select(GrowthCheckIn).where(GrowthCheckIn.enrollment_id == e.id, GrowthCheckIn.week == week)
    )
    now = datetime.now(UTC)
    if c is None:
        db.add(
            GrowthCheckIn(id=uuid.uuid4(), enrollment_id=e.id, week=week, rating=body.rating, updated_at=now)
        )
    else:
        c.rating, c.updated_at = body.rating, now
    try:
        db.commit()
    except IntegrityError:  # a concurrent first save won; this one is retried by the user if needed
        db.rollback()
    return Response(status_code=204)


@router.delete(
    "/programs/{program_id}/weeks/{week}/check-in",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=AUTH,
)
def clear_check_in(program_id: str, week: int, user: CurrentUser, db: Db, content: Content) -> Response:
    p = _program(content, program_id)
    _check_week(p, week)
    e = _required_enrollment(db, user, program_id)
    db.execute(delete(GrowthCheckIn).where(GrowthCheckIn.enrollment_id == e.id, GrowthCheckIn.week == week))
    db.commit()
    return Response(status_code=204)
