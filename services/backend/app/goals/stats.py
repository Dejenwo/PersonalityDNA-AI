"""Habit history and gentle analytics. Pure and deterministic.

Deliberately no streaks: missing a day never resets anything, and the wording elsewhere stays neutral.
"""

from dataclasses import dataclass
from datetime import date, timedelta

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
EVERY_DAY = 0b1111111


def days_to_mask(weekdays: list[int]) -> int:
    """Weekday numbers (0 = Monday ... 6 = Sunday) to a bit mask."""
    if not weekdays or any(not 0 <= d <= 6 for d in weekdays):
        raise ValueError("weekdays must be between 0 (Monday) and 6 (Sunday)")
    return sum(1 << d for d in set(weekdays))


def mask_to_days(mask: int) -> list[int]:
    return [d for d in range(7) if mask & (1 << d)]


def is_planned(mask: int, day: date) -> bool:
    return bool(mask & (1 << day.weekday()))


@dataclass(frozen=True)
class Window:
    days: int
    planned: int
    done_on_planned: int
    done_extra: int  # done on days that were not planned


@dataclass(frozen=True)
class GridDay:
    day: date
    planned: bool
    done: bool


def window(mask: int, done: set[date], start: date, today: date, days: int) -> Window:
    """The last `days` days up to and including today, never before the habit started."""
    first = max(start, today - timedelta(days=days - 1))
    planned = done_planned = extra = 0
    d = first
    while d <= today:
        if is_planned(mask, d):
            planned += 1
            done_planned += d in done
        else:
            extra += d in done
        d += timedelta(days=1)
    return Window(days=days, planned=planned, done_on_planned=done_planned, done_extra=extra)


def grid(mask: int, done: set[date], today: date, weeks: int = 4) -> list[GridDay]:
    """Whole weeks (Monday to Sunday) ending with the week that contains today."""
    last_sunday = today + timedelta(days=6 - today.weekday())
    first = last_sunday - timedelta(days=7 * weeks - 1)
    return [
        GridDay(
            day=first + timedelta(days=i),
            planned=is_planned(mask, first + timedelta(days=i)),
            done=first + timedelta(days=i) in done,
        )
        for i in range(7 * weeks)
    ]
