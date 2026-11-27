from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.billing.plans import Feature, FeatureInfo, Plan


class PlansOut(BaseModel):
    currency: str
    note: str
    free_note: str
    features: list[FeatureInfo]
    plans: list[Plan]
    checkout_available: bool


class SubscriptionOut(BaseModel):
    provider: Literal["stripe", "revenuecat", "dev"]
    plan_id: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool


class BillingOut(BaseModel):
    """What this account can use. When `enforced` is false every feature is available."""

    enforced: bool
    plan_id: str
    plan_name: str
    features: list[Feature]
    coach_daily_messages: int
    subscription: SubscriptionOut | None
    manage_available: bool


class CheckoutIn(BaseModel):
    plan_id: str


class RedirectOut(BaseModel):
    url: str
