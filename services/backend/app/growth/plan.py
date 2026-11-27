"""Turns a growth programme into numbered days. Pure and deterministic.

Each week has seven days: day 1 is the lesson, days 2 to 6 are the week's five daily exercises and day 7
is the milestone with a self-evaluation. Days after the last full week are review days.
"""

from dataclasses import dataclass
from typing import Literal

from app.assessments.content import GrowthAcademy, GrowthProgram

DayKind = Literal["lesson", "exercise", "milestone", "review"]


@dataclass(frozen=True)
class PlanDay:
    day: int
    week: int | None  # 1-based; None for review days
    kind: DayKind
    text: str


def plan_days(academy: GrowthAcademy, program: GrowthProgram) -> list[PlanDay]:
    days: list[PlanDay] = []
    for w_index, week_id in enumerate(program.weeks, start=1):
        week = academy.week(week_id)
        base = (w_index - 1) * 7
        days.append(PlanDay(base + 1, w_index, "lesson", week.lesson.text))
        days.extend(PlanDay(base + 2 + i, w_index, "exercise", text) for i, text in enumerate(week.daily))
        days.append(PlanDay(base + 7, w_index, "milestone", week.milestone))
    first_review = len(program.weeks) * 7 + 1
    days.extend(
        PlanDay(first_review + i, None, "review", academy.review_days[i])
        for i in range(program.days - len(program.weeks) * 7)
    )
    return days


def next_day(total: int, done: set[int]) -> int | None:
    """The first day not yet done, or None when every day is done."""
    return next((d for d in range(1, total + 1) if d not in done), None)
