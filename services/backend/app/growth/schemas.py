from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EnrollmentOut(BaseModel):
    started_at: datetime
    completed_at: datetime | None
    days_done: int
    next_day: int | None


class ProgramSummary(BaseModel):
    id: str
    title: str
    days: int
    kind: Literal["challenge", "program"]
    summary: str
    objectives: list[str]
    topics: list[str]
    enrollment: EnrollmentOut | None


class ProgramList(BaseModel):
    note: str
    programs: list[ProgramSummary]


class DayOut(BaseModel):
    day: int
    kind: Literal["lesson", "exercise", "milestone", "review"]
    text: str
    completed_at: datetime | None


class PracticeOut(BaseModel):
    title: str
    steps: list[str]


class WeekOut(BaseModel):
    number: int
    topic: str
    title: str
    objective: str
    lesson_title: str
    practice: PracticeOut
    self_evaluation: str
    reflection: str
    rating: int | None
    days: list[DayOut]


class ProgramOut(ProgramSummary):
    note: str
    self_evaluation_scale: list[str]
    weeks: list[WeekOut]
    review_days: list[DayOut]


class CheckInIn(BaseModel):
    rating: int = Field(ge=1, le=5)
