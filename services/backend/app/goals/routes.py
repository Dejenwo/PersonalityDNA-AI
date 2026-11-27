"""Goals, milestones and habits. Signed-in users only; everything is scoped to its owner (others get 404)."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser
from app.goals.schemas import (
    GoalIn,
    GoalList,
    GoalOut,
    GoalPatch,
    HabitIn,
    HabitList,
    HabitOut,
    HabitPatch,
    MilestoneIn,
    MilestonePatch,
)
from app.goals.service import GoalService, resolve_today

router = APIRouter(prefix="/api/v1", tags=["goals"], responses={401: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse}}
Today = Annotated[
    date | None,
    Query(description="The user's local date (YYYY-MM-DD); must be within a day of the server's."),
]


def get_goals(request: Request) -> GoalService:
    return GoalService(request.app.state.cipher)


Goals = Annotated[GoalService, Depends(get_goals)]
NO_CONTENT = {"status_code": status.HTTP_204_NO_CONTENT, "response_class": Response, "responses": NOT_FOUND}


@router.get("/goals", response_model=GoalList)
def list_goals(user: CurrentUser, db: Db, svc: Goals) -> GoalList:
    return GoalList(goals=svc.goals(db, user))


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(body: GoalIn, user: CurrentUser, db: Db, svc: Goals) -> GoalOut:
    return svc.create_goal(db, user, body)


@router.get("/goals/{goal_id}", response_model=GoalOut, responses=NOT_FOUND)
def get_goal(goal_id: str, user: CurrentUser, db: Db, svc: Goals) -> GoalOut:
    return svc.goal_out(db, svc.goal(db, user, goal_id))


@router.patch("/goals/{goal_id}", response_model=GoalOut, responses=NOT_FOUND)
def update_goal(goal_id: str, body: GoalPatch, user: CurrentUser, db: Db, svc: Goals) -> GoalOut:
    return svc.update_goal(db, user, goal_id, body)


@router.delete("/goals/{goal_id}", **NO_CONTENT)  # type: ignore[arg-type]
def delete_goal(goal_id: str, user: CurrentUser, db: Db, svc: Goals) -> Response:
    """Deletes the goal and its milestones. Linked habits are kept and unlinked."""
    svc.delete_goal(db, user, goal_id)
    return Response(status_code=204)


@router.post("/goals/{goal_id}/milestones", response_model=GoalOut, status_code=201, responses=NOT_FOUND)
def add_milestone(goal_id: str, body: MilestoneIn, user: CurrentUser, db: Db, svc: Goals) -> GoalOut:
    return svc.add_milestone(db, user, goal_id, body)


@router.patch("/goals/{goal_id}/milestones/{milestone_id}", response_model=GoalOut, responses=NOT_FOUND)
def update_milestone(
    goal_id: str, milestone_id: str, body: MilestonePatch, user: CurrentUser, db: Db, svc: Goals
) -> GoalOut:
    return svc.update_milestone(db, user, goal_id, milestone_id, body)


@router.delete("/goals/{goal_id}/milestones/{milestone_id}", response_model=GoalOut, responses=NOT_FOUND)
def delete_milestone(goal_id: str, milestone_id: str, user: CurrentUser, db: Db, svc: Goals) -> GoalOut:
    return svc.delete_milestone(db, user, goal_id, milestone_id)


@router.get("/habits", response_model=HabitList)
def list_habits(user: CurrentUser, db: Db, svc: Goals, today: Today = None) -> HabitList:
    day = resolve_today(today)
    return HabitList(today=day, habits=svc.habits(db, user, day))


@router.post("/habits", response_model=HabitOut, status_code=status.HTTP_201_CREATED, responses=NOT_FOUND)
def create_habit(body: HabitIn, user: CurrentUser, db: Db, svc: Goals, today: Today = None) -> HabitOut:
    return svc.create_habit(db, user, body, resolve_today(today))


@router.patch("/habits/{habit_id}", response_model=HabitOut, responses=NOT_FOUND)
def update_habit(
    habit_id: str, body: HabitPatch, user: CurrentUser, db: Db, svc: Goals, today: Today = None
) -> HabitOut:
    return svc.update_habit(db, user, habit_id, body, resolve_today(today))


@router.delete("/habits/{habit_id}", **NO_CONTENT)  # type: ignore[arg-type]
def delete_habit(habit_id: str, user: CurrentUser, db: Db, svc: Goals) -> Response:
    svc.delete_habit(db, user, habit_id)
    return Response(status_code=204)


@router.put("/habits/{habit_id}/checks/{day}", response_model=HabitOut, responses=NOT_FOUND)
def check(habit_id: str, day: date, user: CurrentUser, db: Db, svc: Goals, today: Today = None) -> HabitOut:
    """Records that the habit was done on a day (today or up to 30 days back). Idempotent."""
    return svc.set_check(db, user, habit_id, day, True, resolve_today(today))


@router.delete("/habits/{habit_id}/checks/{day}", response_model=HabitOut, responses=NOT_FOUND)
def uncheck(habit_id: str, day: date, user: CurrentUser, db: Db, svc: Goals, today: Today = None) -> HabitOut:
    return svc.set_check(db, user, habit_id, day, False, resolve_today(today))
