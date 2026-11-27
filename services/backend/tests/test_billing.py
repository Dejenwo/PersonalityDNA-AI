"""Plans, entitlements, checkout, provider webhooks, restore and enforcement points."""

import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.api.errors import ApiError
from app.billing.gateways import form_encode
from app.billing.plans import PlanConfig, load_plans
from app.billing.webhooks import verify_stripe_signature
from app.core.config import Settings
from app.database.models import BillingEvent, Subscription
from app.main import create_app
from tests.conftest import CONTENT_DIR
from tests.test_auth import PASSWORD, db, signup
from tests.test_relationships import CONSENT as REL_CONSENT
from tests.test_reports import R, _big_five

B = "/api/v1/billing"
WHSEC = "whsec_test_secret"
RC_AUTH = "rc-shared-secret"


def _client(db_url, **overrides):
    s = Settings(environment="test", database_url=db_url, content_dir=CONTENT_DIR, **overrides)
    return TestClient(create_app(s, create_schema=True))


@pytest.fixture
def enforced(db_url):
    with _client(db_url, billing_enforce=True, billing_dev_checkout=True) as c:
        yield c


class FakeHttp:
    def __init__(self, responses):
        self.calls, self.responses = [], responses

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        for prefix, res in self.responses.items():
            if prefix in url:
                return res
        raise AssertionError(url)


@pytest.fixture
def stripe(db_url):
    with _client(
        db_url,
        billing_enforce=True,
        stripe_secret_key="sk_test_123",
        stripe_webhook_secret=WHSEC,
        stripe_price_ids={"premium-monthly": "price_m", "premium-annual": "price_a"},
        revenuecat_webhook_auth=RC_AUTH,
        revenuecat_api_key="rc_key",
        revenuecat_product_plans={"pdna_premium_annual": "premium-annual"},
    ) as c:
        fake = FakeHttp(
            {
                "/v1/checkout/sessions": {"url": "https://checkout.stripe.com/c/pay_123"},
                "/v1/billing_portal/sessions": {"url": "https://billing.stripe.com/p/session_1"},
            }
        )
        c.app.state.billing.send = fake
        c.fake = fake
        yield c


def _signed(payload: dict, t: int | None = None, secret: str = WHSEC):
    body = json.dumps(payload).encode()
    t = t or int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, {"Stripe-Signature": f"t={t},v1={sig}", "Content-Type": "application/json"}


def _me_id(client, h):
    return client.get("/api/v1/auth/me", headers=h).json()["id"]


# ---------- configuration (pure) ----------


def test_plan_config_and_helpers():
    plans = load_plans()
    assert [p.id for p in plans.paid()] == ["premium-monthly", "premium-annual"]
    assert (
        plans.plan("premium-monthly").price_cents == 999 and plans.plan("premium-annual").price_cents == 6999
    )
    assert plans.plan("free").coach_daily_messages < plans.plan("premium-monthly").coach_daily_messages
    data = plans.model_dump()
    data["plans"][0]["features"] = ["report_pdf"]
    with pytest.raises(ValidationError):
        PlanConfig.model_validate(data)
    assert urllib.parse.parse_qs(
        form_encode({"line_items": [{"price": "p", "quantity": 1}], "a": True}).decode()
    ) == {
        "line_items[0][price]": ["p"],
        "line_items[0][quantity]": ["1"],
        "a": ["true"],
    }
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://x/y",
            jwt_secret="x" * 40,
            email_provider="smtp",
            refresh_cookie_secure=True,
            data_encryption_key="k",
            coach_enabled=False,
            billing_dev_checkout=True,
        )


def test_stripe_signature_verification():
    body = b'{"id":"evt_1"}'
    t = 1_700_000_000
    sig = hmac.new(WHSEC.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    verify_stripe_signature(body, f"t={t},v1=bad,v1={sig}", WHSEC, now=t + 10)
    for header, now in ((f"t={t},v1={sig}", t + 301), (f"t={t},v1={'0' * 64}", t), ("v1=abc", t), (None, t)):
        with pytest.raises(ApiError):
            verify_stripe_signature(body, header, WHSEC, now=now)
    with pytest.raises(ApiError):
        verify_stripe_signature(body + b" ", f"t={t},v1={sig}", WHSEC, now=t)


# ---------- not enforced (the default until the owner sets up billing) ----------


def test_everything_available_until_enforced(client):
    plans = client.get(f"{B}/plans").json()
    assert plans["currency"] == "USD" and plans["checkout_available"] is False
    ada = signup(client)
    me = client.get(f"{B}/me", headers=ada).json()
    assert me["enforced"] is False and me["plan_id"] == "free" and me["subscription"] is None
    assert set(me["features"]) == {f["id"] for f in plans["features"]}
    assert me["coach_daily_messages"] == 30
    r = client.post(f"{B}/checkout", json={"plan_id": "premium-monthly"}, headers=ada)
    assert r.status_code == 503 and r.json()["error"]["code"] == "billing_unavailable"
    assert client.post(f"{B}/manage", headers=ada).status_code == 404
    _big_five(client, ada)
    rep = client.post(R, headers=ada).json()
    assert client.get(f"{R}/{rep['id']}/pdf", headers=ada).status_code == 200
    assert client.post("/api/v1/growth/programs/foundations-30/enrollment", headers=ada).status_code == 200
    # Webhooks refuse to run without their secrets.
    assert client.post(f"{B}/webhooks/stripe", content=b"{}").status_code == 503
    assert client.post(f"{B}/webhooks/revenuecat", content=b"{}").status_code == 503


# ---------- enforced, with the local checkout ----------


def test_free_plan_limits_and_upgrade(enforced):
    c = enforced
    ada = signup(c)
    _big_five(c, ada)
    rep = c.post(R, headers=ada).json()
    r = c.get(f"{R}/{rep['id']}/pdf", headers=ada)
    assert r.status_code == 403 and r.json()["error"]["code"] == "premium_required"
    assert r.json()["error"]["details"]["feature"] == "report_pdf"
    assert c.post("/api/v1/growth/programs/foundations-30/enrollment", headers=ada).status_code == 403
    assert c.post("/api/v1/growth/programs/focus-7/enrollment", headers=ada).status_code == 200
    inv = c.post(
        "/api/v1/relationships/invitations",
        json={"relation_type": "friend", "consent": REL_CONSENT},
        headers=ada,
    )
    assert inv.status_code == 403
    assert c.get("/api/v1/coach/status", headers=ada).json()["daily_limit"] == 5
    # Reports and share cards stay free.
    assert c.post(R, headers=ada).status_code == 201

    assert c.post(f"{B}/checkout", json={"plan_id": "free"}, headers=ada).status_code == 404
    r = c.post(f"{B}/checkout", json={"plan_id": "premium-monthly"}, headers=ada)
    assert r.status_code == 200 and r.json()["url"].endswith("/account?checkout=success")
    me = c.get(f"{B}/me", headers=ada).json()
    assert me["enforced"] and me["plan_id"] == "premium-monthly" and "report_pdf" in me["features"]
    assert me["subscription"]["provider"] == "dev" and me["manage_available"]
    assert c.get(f"{R}/{rep['id']}/pdf", headers=ada).status_code == 200
    assert c.post("/api/v1/growth/programs/foundations-30/enrollment", headers=ada).status_code == 200
    assert c.get("/api/v1/coach/status", headers=ada).json()["daily_limit"] == 30
    r = c.post(f"{B}/checkout", json={"plan_id": "premium-annual"}, headers=ada)
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_subscribed"

    # Cancelling keeps Premium until the period ends; after that the account is free again.
    assert c.post(f"{B}/manage", headers=ada).status_code == 200
    assert c.get(f"{B}/me", headers=ada).json()["subscription"]["cancel_at_period_end"] is True
    with db(c) as s:
        sub = s.scalars(select(Subscription)).one()
        sub.current_period_end = datetime.now(UTC) - timedelta(minutes=1)
        s.commit()
    me = c.get(f"{B}/me", headers=ada).json()
    assert me["plan_id"] == "free" and me["features"] == [] and not me["manage_available"]
    assert c.get(f"{R}/{rep['id']}/pdf", headers=ada).status_code == 403


# ---------- Stripe ----------


def test_stripe_checkout_webhooks_and_portal(stripe):
    c = stripe
    ada = signup(c)
    uid = _me_id(c, ada)
    assert c.get(f"{B}/plans").json()["checkout_available"] is True
    r = c.post(f"{B}/checkout", json={"plan_id": "premium-annual"}, headers=ada)
    assert r.json()["url"] == "https://checkout.stripe.com/c/pay_123"
    method, url, headers, body = c.fake.calls[-1]
    form = urllib.parse.parse_qs(body.decode())
    assert (method, url) == ("POST", "https://api.stripe.com/v1/checkout/sessions")
    assert headers["Authorization"] == "Bearer sk_test_123"
    assert form["client_reference_id"] == [uid] and form["line_items[0][price]"] == ["price_a"]
    assert form["subscription_data[metadata][plan_id]"] == ["premium-annual"]
    assert form["mode"] == ["subscription"] and "customer" not in form

    meta = {"user_id": uid, "plan_id": "premium-annual"}
    done = {
        "id": "evt_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "mode": "subscription",
                "client_reference_id": uid,
                "subscription": "sub_1",
                "customer": "cus_1",
                "metadata": meta,
            }
        },
    }
    body, h = _signed(done)
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 204
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 204  # retry: applied once
    assert c.get(f"{B}/me", headers=ada).json()["plan_id"] == "premium-annual"

    end = int((datetime.now(UTC) + timedelta(days=365)).timestamp())
    upd = {
        "id": "evt_2",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_1",
                "customer": "cus_1",
                "status": "active",
                "cancel_at_period_end": True,
                "items": {"data": [{"current_period_end": end}]},
                "metadata": meta,
            }
        },
    }
    body, h = _signed(upd)
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 204
    sub = c.get(f"{B}/me", headers=ada).json()["subscription"]
    assert sub["cancel_at_period_end"] is True and sub["current_period_end"].startswith(
        datetime.fromtimestamp(end, UTC).date().isoformat()
    )
    r = c.post(f"{B}/manage", headers=ada)
    assert r.json()["url"] == "https://billing.stripe.com/p/session_1"
    assert urllib.parse.parse_qs(c.fake.calls[-1][3].decode())["customer"] == ["cus_1"]

    # Forged or stale events are refused and change nothing.
    body, h = _signed({**upd, "id": "evt_x"}, secret="wrong")
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 400
    body, h = _signed({**upd, "id": "evt_y"}, t=int(time.time()) - 3600)
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 400

    gone = {**upd, "id": "evt_3", "type": "customer.subscription.deleted"}
    body, h = _signed(gone)
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 204
    me = c.get(f"{B}/me", headers=ada).json()
    assert me["plan_id"] == "free" and me["subscription"]["status"] == "canceled"
    with db(c) as s:
        assert sorted(e.event_id for e in s.scalars(select(BillingEvent))) == ["evt_1", "evt_2", "evt_3"]

    # A later checkout reuses the Stripe customer.
    c.post(f"{B}/checkout", json={"plan_id": "premium-monthly"}, headers=ada)
    assert urllib.parse.parse_qs(c.fake.calls[-1][3].decode())["customer"] == ["cus_1"]

    # Events for unknown users or products are recorded and ignored.
    other = {
        **done,
        "id": "evt_4",
        "data": {"object": {**done["data"]["object"], "metadata": {"plan_id": "x"}}},
    }
    body, h = _signed(other)
    assert c.post(f"{B}/webhooks/stripe", content=body, headers=h).status_code == 204


# ---------- RevenueCat (Apple and Google) ----------


def _rc(c, event, auth=RC_AUTH):
    return c.post(
        f"{B}/webhooks/revenuecat", json={"event": event}, headers={"Authorization": f"Bearer {auth}"}
    )


def test_revenuecat_webhooks_and_restore(stripe):
    c = stripe
    ada = signup(c)
    uid = _me_id(c, ada)
    exp = int((datetime.now(UTC) + timedelta(days=365)).timestamp() * 1000)
    base = {
        "app_user_id": uid,
        "product_id": "pdna_premium_annual",
        "original_transaction_id": "1000",
        "expiration_at_ms": exp,
    }
    assert _rc(c, {**base, "id": "rc1", "type": "INITIAL_PURCHASE"}, auth="nope").status_code == 401
    assert _rc(c, {**base, "id": "rc1", "type": "INITIAL_PURCHASE"}).status_code == 204
    me = c.get(f"{B}/me", headers=ada).json()
    assert me["plan_id"] == "premium-annual" and me["subscription"]["provider"] == "revenuecat"
    assert not me["manage_available"]
    r = c.post(f"{B}/manage", headers=ada)
    assert r.status_code == 409 and r.json()["error"]["code"] == "manage_in_store"
    assert _rc(c, {**base, "id": "rc2", "type": "CANCELLATION"}).status_code == 204
    assert c.get(f"{B}/me", headers=ada).json()["subscription"]["cancel_at_period_end"] is True
    assert _rc(c, {**base, "id": "rc3", "type": "EXPIRATION"}).status_code == 204
    assert c.get(f"{B}/me", headers=ada).json()["plan_id"] == "free"
    assert _rc(c, {**base, "id": "rc4", "type": "INITIAL_PURCHASE", "product_id": "other"}).status_code == 204
    assert c.get(f"{B}/me", headers=ada).json()["plan_id"] == "free"

    # Restore reads the subscriber from RevenueCat.
    c.fake.responses["/v1/subscribers/"] = {
        "subscriber": {
            "subscriptions": {
                "pdna_premium_annual": {
                    "expires_date": (datetime.now(UTC) + timedelta(days=30))
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "original_transaction_id": "1000",
                    "unsubscribe_detected_at": None,
                },
                "unknown_product": {"expires_date": None},
            }
        }
    }
    r = c.post(f"{B}/restore", headers=ada)
    assert r.status_code == 200 and r.json()["plan_id"] == "premium-annual"
    method, url, headers, _ = c.fake.calls[-1]
    assert (method, url) == ("GET", f"https://api.revenuecat.com/v1/subscribers/{uid}")
    assert headers["Authorization"] == "Bearer rc_key"


def test_export_ownership_and_account_deletion(enforced):
    c = enforced
    ada = signup(c)
    c.post(f"{B}/checkout", json={"plan_id": "premium-monthly"}, headers=ada)
    subs = c.get("/api/v1/privacy/export", headers=ada).json()["subscriptions"]
    assert [(s["provider"], s["plan"], s["status"]) for s in subs] == [("dev", "premium-monthly", "active")]
    c.cookies.clear()
    bob = signup(c, "bob@example.com")
    assert c.get(f"{B}/me", headers=bob).json()["plan_id"] == "free"
    assert c.post(f"{B}/manage", headers=bob).status_code == 404
    r = c.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204
    with db(c) as s:
        assert s.scalars(select(Subscription)).all() == []
    assert c.get(f"{B}/me").status_code == 401
