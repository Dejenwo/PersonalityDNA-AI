"""In-app and email notifications with per-kind preferences.

Notification text is written by the service and never quotes private content (journal text, goal or habit
titles, coaching messages or results). Security notices can't be turned off; product news is opt-in only.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import Settings
from app.database.models import (
    AssessmentSession,
    GrowthDayProgress,
    GrowthEnrollment,
    Habit,
    HabitCheck,
    Notification,
    NotificationPreference,
    User,
)
from app.goals.stats import is_planned
from app.notifications.email import EmailSender, OutgoingEmail

Kind = Literal[
    "assessment",
    "development",
    "goals",
    "relationships",
    "organisations",
    "subscription",
    "security",
    "news",
]


@dataclass(frozen=True)
class KindInfo:
    label: str
    description: str
    in_app: bool
    email: bool
    required: bool = False


KINDS: dict[str, KindInfo] = {
    "assessment": KindInfo("Assessments", "A reminder when you leave an assessment unfinished.", True, False),
    "development": KindInfo(
        "Growth programmes", "When the next day of a programme you started is ready.", True, False
    ),
    "goals": KindInfo("Habits", "On days you planned habits you haven't checked yet.", True, False),
    "relationships": KindInfo(
        "Relationships", "When someone accepts your invitation to compare.", True, True
    ),
    "organisations": KindInfo("Organisations", "Changes to organisations you belong to.", True, False),
    "subscription": KindInfo("Subscription", "Changes to your plan and payments.", True, True),
    "security": KindInfo("Security", "Sign-in and account security notices. Always on.", True, True, True),
    "news": KindInfo(
        "News and tips", "Occasional product news and tips. Off unless you turn it on.", False, False
    ),
}
PAGE = 30
KEEP_DAYS = 90


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class NotificationService:
    def __init__(self, settings: Settings, sender: EmailSender) -> None:
        self.settings = settings
        self.sender = sender

    # --- preferences ---

    def preferences(self, db: Session, user_id: uuid.UUID) -> dict[str, tuple[bool, bool]]:
        saved = {
            p.kind: (p.in_app, p.email)
            for p in db.scalars(
                select(NotificationPreference).where(NotificationPreference.user_id == user_id)
            )
        }
        out: dict[str, tuple[bool, bool]] = {}
        for kind, info in KINDS.items():
            out[kind] = (True, True) if info.required else saved.get(kind, (info.in_app, info.email))
        return out

    def set_preference(self, db: Session, user_id: uuid.UUID, kind: str, in_app: bool, email: bool) -> None:
        info = KINDS.get(kind)
        if info is None:
            raise ApiError(404, "not_found", "Unknown notification type.")
        if info.required and not (in_app and email):
            raise ApiError(409, "required_notification", "Security notices can't be turned off.")
        row = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id, NotificationPreference.kind == kind
            )
        )
        if row is None:
            row = NotificationPreference(user_id=user_id, kind=kind)
            db.add(row)
        row.in_app, row.email = in_app, email
        db.commit()

    # --- sending ---

    def notify(
        self,
        db: Session,
        user: User,
        kind: Kind,
        title: str,
        body: str = "",
        link: str | None = None,
        dedupe_key: str | None = None,
    ) -> Notification | None:
        """Record and/or email a notification according to the person's preferences. The caller commits."""
        if dedupe_key and db.scalar(
            select(Notification.id).where(
                Notification.user_id == user.id, Notification.dedupe_key == dedupe_key
            )
        ):
            return None
        in_app, email = self.preferences(db, user.id)[kind]
        note = None
        if in_app:
            note = Notification(
                user_id=user.id,
                kind=kind,
                title=title,
                body=body,
                link=link,
                dedupe_key=dedupe_key,
                created_at=_now(),
            )
            db.add(note)
        if email and user.status == "active" and user.email_verified_at is not None:
            url = f"{self.settings.web_base_url.rstrip('/')}{link or '/notifications'}"
            text = (
                f"{body}\n\n{url}\n\n"
                f"Change which emails you get: {self.settings.web_base_url.rstrip('/')}/notifications"
            )
            self.sender.send(
                OutgoingEmail(to=user.email, subject=title, text=text.strip(), kind=f"notify_{kind}")
            )
        return note

    # --- reading ---

    def list(
        self, db: Session, user_id: uuid.UUID, before: datetime | None = None
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if before is not None:
            stmt = stmt.where(Notification.created_at < before)
        rows = list(db.scalars(stmt.order_by(Notification.created_at.desc()).limit(PAGE)))
        unread = db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        return rows, unread or 0

    def mark_read(self, db: Session, user_id: uuid.UUID, notification_id: uuid.UUID | None) -> None:
        stmt = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        if notification_id is not None:
            if (
                db.scalar(
                    select(Notification.id).where(
                        Notification.id == notification_id, Notification.user_id == user_id
                    )
                )
                is None
            ):
                raise ApiError(404, "not_found", "Notification not found.")
            stmt = stmt.where(Notification.id == notification_id)
        db.execute(stmt.values(read_at=_now()))
        db.commit()

    # --- scheduled reminders (scripts/send_reminders.py) ---

    def send_reminders(self, db: Session, today: date | None = None) -> dict[str, int]:
        """Daily reminders. Each is sent at most once (dedupe key), and only to active, verified accounts."""
        today = today or _now().date()
        sent = {"assessment": 0, "development": 0, "goals": 0}
        cutoff = _now() - timedelta(hours=24)
        users: dict[uuid.UUID, User | None] = {}

        def person(uid: uuid.UUID) -> User | None:
            if uid not in users:
                u = db.get(User, uid)
                users[uid] = u if u and u.status == "active" and u.email_verified_at else None
            return users[uid]

        for s in db.scalars(
            select(AssessmentSession).where(
                AssessmentSession.user_id.is_not(None),
                AssessmentSession.status == "in_progress",
                AssessmentSession.updated_at < cutoff,
            )
        ):
            u = person(cast(uuid.UUID, s.user_id))
            if u and self.notify(
                db,
                u,
                "assessment",
                "Your assessment is waiting",
                "You can pick up where you left off. Your answers so far are saved.",
                "/history",
                f"assessment:{s.id}",
            ):
                sent["assessment"] += 1

        for e in db.scalars(select(GrowthEnrollment).where(GrowthEnrollment.completed_at.is_(None))):
            u = person(e.user_id)
            if u is None:
                continue
            day = (today - _aware(e.started_at).date()).days + 1
            done = db.scalar(
                select(GrowthDayProgress.id).where(
                    GrowthDayProgress.enrollment_id == e.id, GrowthDayProgress.day == day
                )
            )
            if (
                day >= 1
                and done is None
                and self.notify(
                    db,
                    u,
                    "development",
                    f"Day {day} of your programme is ready",
                    "A few minutes today keeps your practice going.",
                    f"/growth/{e.program_id}",
                    f"growth:{e.id}:{today.isoformat()}",
                )
            ):
                sent["development"] += 1

        planned: dict[uuid.UUID, int] = {}
        for h in db.scalars(select(Habit).where(Habit.archived_at.is_(None), Habit.start_date <= today)):
            checked = db.scalar(
                select(HabitCheck.id).where(HabitCheck.habit_id == h.id, HabitCheck.day == today)
            )
            if is_planned(h.days, today) and checked is None:
                planned[h.user_id] = planned.get(h.user_id, 0) + 1
        for uid, n in planned.items():
            u = person(uid)
            habits = "habit" if n == 1 else "habits"
            if u and self.notify(
                db,
                u,
                "goals",
                f"You planned {n} {habits} for today",
                "Check them off when you're done, or skip today. Either is fine.",
                "/goals",
                f"habits:{today.isoformat()}",
            ):
                sent["goals"] += 1

        old = _now() - timedelta(days=KEEP_DAYS)
        db.execute(delete(Notification).where(Notification.created_at < old))
        db.commit()
        return sent
