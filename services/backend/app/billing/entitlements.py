"""The one place features ask "can this account use X?". Providers only write subscriptions."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.billing.plans import Feature, Plan, PlanConfig, load_plans
from app.core.config import Settings
from app.database.models import Subscription

ACTIVE = ("active", "trialing", "past_due")


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def is_current(s: Subscription, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return s.status in ACTIVE and (s.current_period_end is None or _aware(s.current_period_end) > now)


class Entitlements:
    def __init__(self, settings: Settings, plans: PlanConfig | None = None) -> None:
        self.settings = settings
        self.plans = plans or load_plans()

    def subscription(self, db: Session, user_id: uuid.UUID) -> Subscription | None:
        """The current subscription with the most features (then the latest end), else the newest one."""
        rows = list(
            db.scalars(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .order_by(Subscription.updated_at.desc())
            )
        )
        current = [s for s in rows if is_current(s) and self._known(s.plan_id)]
        if current:
            return max(
                current,
                key=lambda s: (
                    len(self.plans.plan(s.plan_id).features),
                    _aware(s.current_period_end or datetime.max.replace(tzinfo=UTC)),
                ),
            )
        return rows[0] if rows else None

    def _known(self, plan_id: str) -> bool:
        try:
            self.plans.plan(plan_id)
        except KeyError:
            return False
        return True

    def plan(self, db: Session, user_id: uuid.UUID) -> Plan:
        s = self.subscription(db, user_id)
        return self.plans.plan(s.plan_id) if s is not None and is_current(s) else self.plans.plan("free")

    def has(self, db: Session, user_id: uuid.UUID, feature: Feature) -> bool:
        return not self.settings.billing_enforce or feature in self.plan(db, user_id).features

    def require(self, db: Session, user_id: uuid.UUID, feature: Feature) -> None:
        if not self.has(db, user_id, feature):
            label = next(f.label for f in self.plans.features if f.id == feature)
            raise ApiError(
                403,
                "premium_required",
                f"{label} are part of Premium.",
                {"feature": feature, "pricing_url": "/pricing"},
            )

    def coach_daily_messages(self, db: Session, user_id: uuid.UUID) -> int:
        if not self.settings.billing_enforce:
            return self.settings.coach_daily_message_limit
        return self.plan(db, user_id).coach_daily_messages
