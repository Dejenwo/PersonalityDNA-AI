from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

GoalStatus = Literal["active", "completed", "archived"]
Title = Field(min_length=1, max_length=200)


class MilestoneIn(BaseModel):
    title: str = Title
    due_date: date | None = None


class MilestonePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: date | None = None
    done: bool | None = None


class MilestoneOut(BaseModel):
    id: str
    title: str
    due_date: date | None
    done_at: datetime | None


class GoalIn(BaseModel):
    title: str = Title
    why: str | None = Field(default=None, max_length=1000)
    target_date: date | None = None
    milestones: list[MilestoneIn] = Field(default_factory=list, max_length=20)


class GoalPatch(BaseModel):
    """Only the fields that are sent change. Send null to clear the reason or target date."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    why: str | None = Field(default=None, max_length=1000)
    target_date: date | None = None
    status: GoalStatus | None = None


class GoalOut(BaseModel):
    id: str
    title: str
    why: str | None
    target_date: date | None
    status: GoalStatus
    created_at: datetime
    completed_at: datetime | None
    milestones: list[MilestoneOut]
    milestones_done: int
    habits: list[str]  # ids of habits linked to this goal


class GoalList(BaseModel):
    goals: list[GoalOut]


class HabitIn(BaseModel):
    title: str = Title
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    goal_id: str | None = None


class HabitPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    weekdays: list[int] | None = Field(default=None, min_length=1, max_length=7)
    goal_id: str | None = None
    archived: bool | None = None


class WindowOut(BaseModel):
    days: int
    planned: int
    done_on_planned: int
    done_extra: int


class GridDayOut(BaseModel):
    day: date
    planned: bool
    done: bool


class HabitOut(BaseModel):
    id: str
    title: str
    weekdays: list[int]
    goal_id: str | None
    start_date: date
    archived: bool
    done_today: bool
    planned_today: bool
    last_7: WindowOut
    last_30: WindowOut
    grid: list[GridDayOut]


class HabitList(BaseModel):
    today: date
    habits: list[HabitOut]
