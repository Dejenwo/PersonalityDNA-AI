"""Personal goals with milestones, and habits with completion history. Titles and reasons are encrypted at
rest; every query is scoped to the owner. Nothing here logs user text."""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.database.models import Goal, GoalMilestone, Habit, HabitCheck, User
from app.goals import stats
from app.goals.schemas import (
    GoalIn,
    GoalOut,
    GoalPatch,
    GridDayOut,
    HabitIn,
    HabitOut,
    HabitPatch,
    MilestoneIn,
    MilestoneOut,
    MilestonePatch,
    WindowOut,
)
from app.security.crypto import FieldCipher

MAX_GOALS = 100
MAX_MILESTONES = 20
MAX_HABITS = 50
BACKFILL_DAYS = 30


def resolve_today(asked: date | None) -> date:
    """The user's local date. Accepted when within a day of the server's UTC date (time zones)."""
    server = datetime.now(UTC).date()
    if asked is None:
        return server
    if abs((asked - server).days) > 1:
        raise ApiError(422, "invalid_today", "The date does not match the current date.")
    return asked


def _uuid(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ApiError(404, "not_found", f"{what} not found.") from None


class GoalService:
    def __init__(self, cipher: FieldCipher) -> None:
        self.cipher = cipher

    def _enc(self, text: str, row: uuid.UUID, field: str) -> str:
        return self.cipher.encrypt(text, f"{field}:{row}")

    def _dec(self, stored: str, row: uuid.UUID, field: str) -> str:
        return self.cipher.decrypt(stored, f"{field}:{row}")

    # ---------- goals ----------

    def goal(self, db: Session, user: User, goal_id: str) -> Goal:
        g = db.get(Goal, _uuid(goal_id, "Goal"))
        if g is None or g.user_id != user.id:
            raise ApiError(404, "not_found", "Goal not found.")
        return g

    def goal_out(self, db: Session, g: Goal) -> GoalOut:
        ms = db.scalars(
            select(GoalMilestone).where(GoalMilestone.goal_id == g.id).order_by(GoalMilestone.position)
        ).all()
        habit_ids = db.scalars(select(Habit.id).where(Habit.goal_id == g.id).order_by(Habit.created_at)).all()
        return GoalOut(
            id=str(g.id),
            title=self._dec(g.title_encrypted, g.id, "goal-title"),
            why=self._dec(g.why_encrypted, g.id, "goal-why") if g.why_encrypted else None,
            target_date=g.target_date,
            status=g.status,
            created_at=g.created_at,
            completed_at=g.completed_at,
            milestones=[
                MilestoneOut(
                    id=str(m.id),
                    title=self._dec(m.title_encrypted, m.id, "milestone-title"),
                    due_date=m.due_date,
                    done_at=m.done_at,
                )
                for m in ms
            ],
            milestones_done=sum(1 for m in ms if m.done_at),
            habits=[str(h) for h in habit_ids],
        )

    def goals(self, db: Session, user: User) -> list[GoalOut]:
        rows = db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc()))
        order = {"active": 0, "completed": 1, "archived": 2}
        return sorted((self.goal_out(db, g) for g in rows), key=lambda g: order[g.status])

    def create_goal(self, db: Session, user: User, body: GoalIn) -> GoalOut:
        count = db.scalar(select(func.count()).select_from(Goal).where(Goal.user_id == user.id)) or 0
        if count >= MAX_GOALS:
            raise ApiError(
                409, "too_many_goals", f"You can keep up to {MAX_GOALS} goals. Delete one to add another."
            )
        now = datetime.now(UTC)
        g = Goal(
            id=uuid.uuid4(),
            user_id=user.id,
            target_date=body.target_date,
            status="active",
            created_at=now,
            updated_at=now,
        )
        g.title_encrypted = self._enc(body.title.strip(), g.id, "goal-title")
        why = (body.why or "").strip()
        g.why_encrypted = self._enc(why, g.id, "goal-why") if why else None
        db.add(g)
        for i, m in enumerate(body.milestones):
            self._add_milestone(db, g, m, i)
        db.commit()
        return self.goal_out(db, g)

    def update_goal(self, db: Session, user: User, goal_id: str, patch: GoalPatch) -> GoalOut:
        g = self.goal(db, user, goal_id)
        sent = patch.model_fields_set
        if "title" in sent and patch.title:
            g.title_encrypted = self._enc(patch.title.strip(), g.id, "goal-title")
        if "why" in sent:
            why = (patch.why or "").strip()
            g.why_encrypted = self._enc(why, g.id, "goal-why") if why else None
        if "target_date" in sent:
            g.target_date = patch.target_date
        if "status" in sent and patch.status and patch.status != g.status:
            g.status = patch.status
            g.completed_at = datetime.now(UTC) if patch.status == "completed" else None
        g.updated_at = datetime.now(UTC)
        db.commit()
        return self.goal_out(db, g)

    def delete_goal(self, db: Session, user: User, goal_id: str) -> None:
        g = self.goal(db, user, goal_id)
        # Linked habits are kept and simply unlinked (FK SET NULL; done here too for SQLite sessions).
        for h in db.scalars(select(Habit).where(Habit.goal_id == g.id)):
            h.goal_id = None
        db.delete(g)
        db.commit()

    # ---------- milestones ----------

    def _add_milestone(self, db: Session, g: Goal, body: MilestoneIn, position: int) -> GoalMilestone:
        m = GoalMilestone(
            id=uuid.uuid4(),
            goal_id=g.id,
            due_date=body.due_date,
            position=position,
            created_at=datetime.now(UTC),
        )
        m.title_encrypted = self._enc(body.title.strip(), m.id, "milestone-title")
        db.add(m)
        return m

    def add_milestone(self, db: Session, user: User, goal_id: str, body: MilestoneIn) -> GoalOut:
        g = self.goal(db, user, goal_id)
        last = db.scalar(select(func.max(GoalMilestone.position)).where(GoalMilestone.goal_id == g.id))
        count = db.scalar(
            select(func.count()).select_from(GoalMilestone).where(GoalMilestone.goal_id == g.id)
        )
        if (count or 0) >= MAX_MILESTONES:
            raise ApiError(409, "too_many_milestones", f"A goal can have up to {MAX_MILESTONES} milestones.")
        self._add_milestone(db, g, body, (last if last is not None else -1) + 1)
        g.updated_at = datetime.now(UTC)
        db.commit()
        return self.goal_out(db, g)

    def _milestone(self, db: Session, g: Goal, milestone_id: str) -> GoalMilestone:
        m = db.get(GoalMilestone, _uuid(milestone_id, "Milestone"))
        if m is None or m.goal_id != g.id:
            raise ApiError(404, "not_found", "Milestone not found.")
        return m

    def update_milestone(
        self, db: Session, user: User, goal_id: str, milestone_id: str, patch: MilestonePatch
    ) -> GoalOut:
        g = self.goal(db, user, goal_id)
        m = self._milestone(db, g, milestone_id)
        sent = patch.model_fields_set
        if "title" in sent and patch.title:
            m.title_encrypted = self._enc(patch.title.strip(), m.id, "milestone-title")
        if "due_date" in sent:
            m.due_date = patch.due_date
        if "done" in sent and patch.done is not None:
            if patch.done and m.done_at is None:
                m.done_at = datetime.now(UTC)
            elif not patch.done:
                m.done_at = None
        g.updated_at = datetime.now(UTC)
        db.commit()
        return self.goal_out(db, g)

    def delete_milestone(self, db: Session, user: User, goal_id: str, milestone_id: str) -> GoalOut:
        g = self.goal(db, user, goal_id)
        db.delete(self._milestone(db, g, milestone_id))
        db.commit()
        return self.goal_out(db, g)

    # ---------- habits ----------

    def habit(self, db: Session, user: User, habit_id: str) -> Habit:
        h = db.get(Habit, _uuid(habit_id, "Habit"))
        if h is None or h.user_id != user.id:
            raise ApiError(404, "not_found", "Habit not found.")
        return h

    def habit_out(self, db: Session, h: Habit, today: date) -> HabitOut:
        since = today - timedelta(days=40)
        done = set(
            db.scalars(select(HabitCheck.day).where(HabitCheck.habit_id == h.id, HabitCheck.day >= since))
        )

        def win(n: int) -> WindowOut:
            w = stats.window(h.days, done, h.start_date, today, n)
            return WindowOut(
                days=w.days, planned=w.planned, done_on_planned=w.done_on_planned, done_extra=w.done_extra
            )

        return HabitOut(
            id=str(h.id),
            title=self._dec(h.title_encrypted, h.id, "habit-title"),
            weekdays=stats.mask_to_days(h.days),
            goal_id=str(h.goal_id) if h.goal_id else None,
            start_date=h.start_date,
            archived=h.archived_at is not None,
            done_today=today in done,
            planned_today=stats.is_planned(h.days, today),
            last_7=win(7),
            last_30=win(30),
            grid=[
                GridDayOut(day=d.day, planned=d.planned, done=d.done) for d in stats.grid(h.days, done, today)
            ],
        )

    def habits(self, db: Session, user: User, today: date) -> list[HabitOut]:
        rows = db.scalars(select(Habit).where(Habit.user_id == user.id).order_by(Habit.created_at))
        out = [self.habit_out(db, h, today) for h in rows]
        return sorted(out, key=lambda h: h.archived)

    def _linked_goal(self, db: Session, user: User, goal_id: str | None) -> uuid.UUID | None:
        return self.goal(db, user, goal_id).id if goal_id else None

    def create_habit(self, db: Session, user: User, body: HabitIn, today: date) -> HabitOut:
        count = db.scalar(select(func.count()).select_from(Habit).where(Habit.user_id == user.id)) or 0
        if count >= MAX_HABITS:
            raise ApiError(
                409, "too_many_habits", f"You can keep up to {MAX_HABITS} habits. Delete one to add another."
            )
        h = Habit(
            id=uuid.uuid4(),
            user_id=user.id,
            goal_id=self._linked_goal(db, user, body.goal_id),
            days=_mask(body.weekdays),
            start_date=today,
            created_at=datetime.now(UTC),
        )
        h.title_encrypted = self._enc(body.title.strip(), h.id, "habit-title")
        db.add(h)
        db.commit()
        return self.habit_out(db, h, today)

    def update_habit(
        self, db: Session, user: User, habit_id: str, patch: HabitPatch, today: date
    ) -> HabitOut:
        h = self.habit(db, user, habit_id)
        sent = patch.model_fields_set
        if "title" in sent and patch.title:
            h.title_encrypted = self._enc(patch.title.strip(), h.id, "habit-title")
        if "weekdays" in sent and patch.weekdays:
            h.days = _mask(patch.weekdays)
        if "goal_id" in sent:
            h.goal_id = self._linked_goal(db, user, patch.goal_id)
        if "archived" in sent and patch.archived is not None:
            h.archived_at = (h.archived_at or datetime.now(UTC)) if patch.archived else None
        db.commit()
        return self.habit_out(db, h, today)

    def delete_habit(self, db: Session, user: User, habit_id: str) -> None:
        db.delete(self.habit(db, user, habit_id))
        db.commit()

    def set_check(
        self, db: Session, user: User, habit_id: str, day: date, done: bool, today: date
    ) -> HabitOut:
        h = self.habit(db, user, habit_id)
        if day > today or day < today - timedelta(days=BACKFILL_DAYS):
            raise ApiError(422, "invalid_day", f"You can record today or up to {BACKFILL_DAYS} days back.")
        if done:
            exists = db.scalar(
                select(HabitCheck.id).where(HabitCheck.habit_id == h.id, HabitCheck.day == day)
            )
            if exists is None:
                db.add(HabitCheck(id=uuid.uuid4(), habit_id=h.id, day=day, created_at=datetime.now(UTC)))
                if day < h.start_date:
                    h.start_date = day
        else:
            db.execute(delete(HabitCheck).where(HabitCheck.habit_id == h.id, HabitCheck.day == day))
        db.commit()
        return self.habit_out(db, h, today)

    # ---------- export ----------

    def export(self, db: Session, user: User) -> dict[str, object]:
        today = datetime.now(UTC).date()
        habits = []
        for h in db.scalars(select(Habit).where(Habit.user_id == user.id)):
            out = self.habit_out(db, h, today).model_dump(
                mode="json", include={"id", "title", "weekdays", "goal_id"}
            )
            out["days_done"] = [
                d.isoformat() for d in db.scalars(select(HabitCheck.day).where(HabitCheck.habit_id == h.id))
            ]
            habits.append(out)
        return {"goals": [g.model_dump(mode="json") for g in self.goals(db, user)], "habits": habits}


def _mask(weekdays: list[int]) -> int:
    try:
        return stats.days_to_mask(weekdays)
    except ValueError as exc:
        raise ApiError(422, "invalid_weekdays", "Choose days between Monday and Sunday.") from exc
