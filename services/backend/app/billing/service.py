"""Billing: plans, the account's entitlements, checkout, managing a subscription and restoring purchases."""

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.billing.entitlements import Entitlements, is_current
from app.billing.gateways import RevenueCatClient, Sender, StripeClient, http_send
from app.billing.schemas import BillingOut, PlansOut, SubscriptionOut
from app.billing.webhooks import (
    apply_revenuecat_event,
    apply_stripe_event,
    parse_json,
    upsert,
    verify_stripe_signature,
)
from app.core.config import Settings
from app.database.models import Subscription, User

DEV_PERIOD = timedelta(days=30)


class BillingService:
    def __init__(self, settings: Settings, entitlements: Entitlements, send: Sender = http_send) -> None:
        self.settings, self.entitlements, self.send = settings, entitlements, send
        self.plans = entitlements.plans

    # --- configuration ---

    def stripe(self) -> StripeClient | None:
        key = self.settings.stripe_secret_key
        return StripeClient(key.get_secret_value(), self.settings.stripe_api_base, self.send) if key else None

    def revenuecat(self) -> RevenueCatClient | None:
        key = self.settings.revenuecat_api_key
        if key is None:
            return None
        return RevenueCatClient(key.get_secret_value(), self.settings.revenuecat_api_base, self.send)

    def checkout_available(self) -> bool:
        return self.settings.billing_dev_checkout or (
            self.stripe() is not None and bool(self.settings.stripe_price_ids)
        )

    # --- reading ---

    def plans_out(self) -> PlansOut:
        p = self.plans
        return PlansOut(
            currency=p.currency,
            note=p.note,
            free_note=p.free_note,
            features=p.features,
            plans=p.plans,
            checkout_available=self.checkout_available(),
        )

    def me(self, db: Session, user: User) -> BillingOut:
        s = self.entitlements.subscription(db, user.id)
        plan = self.entitlements.plan(db, user.id)
        enforced = self.settings.billing_enforce
        return BillingOut(
            enforced=enforced,
            plan_id=plan.id,
            plan_name=plan.name,
            features=plan.features if enforced else [f.id for f in self.plans.features],
            coach_daily_messages=self.entitlements.coach_daily_messages(db, user.id),
            subscription=SubscriptionOut(
                provider=s.provider,
                plan_id=s.plan_id,
                status=s.status,
                current_period_end=s.current_period_end.replace(tzinfo=UTC)
                if s.current_period_end and s.current_period_end.tzinfo is None
                else s.current_period_end,
                cancel_at_period_end=s.cancel_at_period_end,
            )
            if s is not None
            else None,
            manage_available=s is not None and s.provider in ("stripe", "dev") and is_current(s),
        )

    # --- changing ---

    def checkout(self, db: Session, user: User, plan_id: str) -> str:
        if plan_id not in {p.id for p in self.plans.paid()}:
            raise ApiError(404, "not_found", "Plan not found.")
        current = self.entitlements.subscription(db, user.id)
        if current is not None and is_current(current):
            raise ApiError(
                409, "already_subscribed", "You already have Premium. Manage it from your account."
            )
        base = self.settings.web_base_url.rstrip("/")
        stripe = self.stripe()
        price = self.settings.stripe_price_ids.get(plan_id)
        if stripe is not None and price:
            return stripe.checkout_session(
                user_id=str(user.id),
                plan_id=plan_id,
                price_id=price,
                customer_id=self._customer(db, user),
                success_url=f"{base}/account?checkout=success",
                cancel_url=f"{base}/pricing?checkout=cancelled",
            )
        if self.settings.billing_dev_checkout:
            upsert(
                db,
                user=user,
                provider="dev",
                ref=f"dev-{uuid.uuid4()}",
                plan_id=plan_id,
                status="active",
                period_end=datetime.now(UTC) + DEV_PERIOD,
                cancel_at_period_end=False,
            )
            db.commit()
            return f"{base}/account?checkout=success"
        raise ApiError(503, "billing_unavailable", "Subscriptions aren't available yet.")

    def _customer(self, db: Session, user: User) -> str | None:
        return db.scalar(
            select(Subscription.provider_customer_id)
            .where(
                Subscription.user_id == user.id,
                Subscription.provider == "stripe",
                Subscription.provider_customer_id.is_not(None),
            )
            .order_by(Subscription.updated_at.desc())
            .limit(1)
        )

    def manage(self, db: Session, user: User) -> str:
        """Where to change or cancel. Stripe's customer portal on the web; app stores manage their own."""
        s = self.entitlements.subscription(db, user.id)
        base = self.settings.web_base_url.rstrip("/")
        if s is None or not is_current(s):
            raise ApiError(404, "no_subscription", "You don't have an active subscription.")
        if s.provider == "revenuecat":
            raise ApiError(
                409,
                "manage_in_store",
                "Manage this subscription in the App Store or Google Play where you bought it.",
            )
        if s.provider == "dev":
            s.cancel_at_period_end = not s.cancel_at_period_end
            s.updated_at = datetime.now(UTC)
            db.commit()
            return f"{base}/account"
        stripe = self.stripe()
        if stripe is None or not s.provider_customer_id:
            raise ApiError(503, "billing_unavailable", "Managing subscriptions isn't available right now.")
        return stripe.portal_session(customer_id=s.provider_customer_id, return_url=f"{base}/account")

    def restore(self, db: Session, user: User) -> BillingOut:
        """Re-reads app store purchases from RevenueCat (the "Restore purchases" button in the apps)."""
        rc = self.revenuecat()
        if rc is None:
            raise ApiError(503, "billing_unavailable", "Restoring purchases isn't available right now.")
        data = rc.subscriber(str(user.id))
        subs: dict[str, Any] = (data.get("subscriber") or {}).get("subscriptions") or {}
        for product, info in subs.items():
            plan_id = self.settings.revenuecat_product_plans.get(product)
            if plan_id is None:
                continue
            expires = _iso(info.get("expires_date"))
            status = "active" if expires is None or expires > datetime.now(UTC) else "expired"
            if info.get("billing_issues_detected_at") and status == "active":
                status = "past_due"
            upsert(
                db,
                user=user,
                provider="revenuecat",
                ref=str(info.get("original_transaction_id") or f"{user.id}:{product}"),
                plan_id=plan_id,
                status=status,
                period_end=expires,
                cancel_at_period_end=bool(info.get("unsubscribe_detected_at")),
            )
        db.commit()
        return self.me(db, user)

    # --- webhooks ---

    def stripe_webhook(self, db: Session, payload: bytes, signature: str | None) -> None:
        secret = self.settings.stripe_webhook_secret
        if secret is None:
            raise ApiError(503, "billing_unavailable", "Stripe webhooks are not configured.")
        verify_stripe_signature(payload, signature, secret.get_secret_value())
        apply_stripe_event(db, self.plans, parse_json(payload))

    def revenuecat_webhook(self, db: Session, payload: bytes, authorization: str | None) -> None:
        secret = self.settings.revenuecat_webhook_auth
        if secret is None:
            raise ApiError(503, "billing_unavailable", "RevenueCat webhooks are not configured.")
        expected = secret.get_secret_value()
        given = (authorization or "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(given.encode(), expected.encode()):
            raise ApiError(401, "unauthorized", "Invalid webhook authorization.")
        event = parse_json(payload).get("event")
        if not isinstance(event, dict):
            raise ApiError(400, "invalid_payload", "Missing event.")
        apply_revenuecat_event(db, self.settings.revenuecat_product_plans, event)


def _iso(value: Any) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
