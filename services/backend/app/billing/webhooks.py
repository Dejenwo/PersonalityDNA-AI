"""Applies provider webhook events to subscriptions. Each event is applied once (billing_events)."""

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.billing.plans import PlanConfig
from app.database.models import BillingEvent, Subscription, User

STRIPE_TOLERANCE_SECONDS = 300
SUBSCRIPTION_EVENTS = (
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
)
STRIPE_STATUS = {
    "active": "active",
    "trialing": "trialing",
    "past_due": "past_due",
    "unpaid": "past_due",
    "incomplete": "incomplete",
    "incomplete_expired": "expired",
    "canceled": "canceled",
    "paused": "canceled",
}


def verify_stripe_signature(
    payload: bytes, header: str | None, secret: str, now: float | None = None
) -> None:
    """Stripe-Signature: t=<unix time>,v1=<hex HMAC-SHA256 of "t.payload">. Rejects stale or forged events."""
    bad = ApiError(400, "invalid_signature", "Invalid webhook signature.")
    if not header:
        raise bad
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        k, _, v = item.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        ts = int(parts["t"][0])
    except (KeyError, ValueError):
        raise bad from None
    if abs((now if now is not None else time.time()) - ts) > STRIPE_TOLERANCE_SECONDS:
        raise bad
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", [])):
        raise bad


def _first_event(
    db: Session, provider: str, event_id: str, event_type: str, user_id: uuid.UUID | None
) -> bool:
    """Records the event; False if it was already processed."""
    if db.scalar(
        select(BillingEvent.id).where(BillingEvent.provider == provider, BillingEvent.event_id == event_id)
    ):
        return False
    db.add(
        BillingEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type[:64],
            user_id=user_id,
            received_at=datetime.now(UTC),
        )
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return False
    return True


def _user(db: Session, raw: Any) -> User | None:
    try:
        return db.get(User, uuid.UUID(str(raw)))
    except ValueError:
        return None


def _ts(value: Any) -> datetime | None:
    return datetime.fromtimestamp(int(value), UTC) if value else None


def upsert(
    db: Session,
    *,
    user: User,
    provider: str,
    ref: str,
    plan_id: str,
    status: str,
    period_end: datetime | None,
    cancel_at_period_end: bool,
    customer_id: str | None = None,
) -> Subscription:
    s = db.scalar(
        select(Subscription).where(
            Subscription.provider == provider, Subscription.provider_subscription_id == ref
        )
    )
    now = datetime.now(UTC)
    if s is None:
        s = Subscription(
            id=uuid.uuid4(), user_id=user.id, provider=provider, provider_subscription_id=ref, created_at=now
        )
        db.add(s)
    s.plan_id, s.status, s.current_period_end = plan_id, status, period_end
    s.cancel_at_period_end = cancel_at_period_end
    if customer_id:
        s.provider_customer_id = customer_id
    s.updated_at = now
    return s


def apply_stripe_event(db: Session, plans: PlanConfig, event: dict[str, Any]) -> None:
    kind = str(event.get("type", ""))
    obj: dict[str, Any] = event.get("data", {}).get("object", {}) or {}
    meta: dict[str, Any] = obj.get("metadata") or {}
    user = _user(db, obj.get("client_reference_id") or meta.get("user_id"))
    if not _first_event(db, "stripe", str(event.get("id", "")), kind, user.id if user else None):
        return
    plan_id = str(meta.get("plan_id", ""))
    known = plan_id in {p.id for p in plans.paid()}
    if user is None or not known:
        db.commit()  # recorded, nothing to apply (another product, or not ours)
        return
    if kind == "checkout.session.completed" and obj.get("mode") == "subscription" and obj.get("subscription"):
        upsert(
            db,
            user=user,
            provider="stripe",
            ref=str(obj["subscription"]),
            plan_id=plan_id,
            status="active",
            period_end=None,
            cancel_at_period_end=False,
            customer_id=obj.get("customer"),
        )
    elif kind in SUBSCRIPTION_EVENTS:
        items = (obj.get("items") or {}).get("data") or [{}]
        period_end = obj.get("current_period_end") or items[0].get("current_period_end")
        status = STRIPE_STATUS.get(str(obj.get("status")), "incomplete")
        if kind.endswith("deleted"):
            status = "canceled"
        upsert(
            db,
            user=user,
            provider="stripe",
            ref=str(obj["id"]),
            plan_id=plan_id,
            status=status,
            period_end=_ts(period_end),
            cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
            customer_id=obj.get("customer"),
        )
    db.commit()


def parse_json(payload: bytes) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except ValueError:
        raise ApiError(400, "invalid_payload", "The webhook body is not JSON.") from None
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_payload", "The webhook body is not an object.")
    return data


RC_ACTIVE = ("INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION", "PRODUCT_CHANGE", "SUBSCRIPTION_EXTENDED")


def apply_revenuecat_event(db: Session, product_plans: dict[str, str], event: dict[str, Any]) -> None:
    kind = str(event.get("type", ""))
    user = _user(db, event.get("app_user_id") or event.get("original_app_user_id"))
    if not _first_event(db, "revenuecat", str(event.get("id", "")), kind, user.id if user else None):
        return
    product = str(event.get("product_id", ""))
    plan_id = product_plans.get(product)
    if user is None or plan_id is None or kind == "TEST":
        db.commit()
        return
    ref = str(event.get("original_transaction_id") or f"{user.id}:{product}")
    expires = event.get("expiration_at_ms")
    period_end = datetime.fromtimestamp(int(expires) / 1000, UTC) if expires else None
    status, cancel = "active", False
    if kind == "CANCELLATION":
        cancel = True
    elif kind == "EXPIRATION":
        status = "expired"
    elif kind == "BILLING_ISSUE":
        status = "past_due"
    elif kind not in RC_ACTIVE:
        db.commit()
        return
    upsert(
        db,
        user=user,
        provider="revenuecat",
        ref=ref,
        plan_id=plan_id,
        status=status,
        period_end=period_end,
        cancel_at_period_end=cancel,
    )
    db.commit()
