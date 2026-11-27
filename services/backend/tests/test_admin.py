"""Admin portal: least-privilege roles, support actions with audit, aggregates without private content."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.admin.roles import ROLES, permissions
from app.core.config import Settings
from app.database.models import AdminRole, AuditEvent, User
from app.main import create_app
from scripts.grant_admin import main as grant_cli
from tests.conftest import CONTENT_DIR
from tests.test_auth import PASSWORD, db, signup
from tests.test_coach import Scripted, new_conversation, send, use
from tests.test_reports import R, _big_five

A = "/api/v1/admin"


def _uid(client, h):
    return client.get("/api/v1/auth/me", headers=h).json()["id"]


def _grant(client, h, *roles):
    uid = uuid.UUID(_uid(client, h))
    with db(client) as s:
        for r in roles:
            s.add(AdminRole(user_id=uid, role=r, created_at=datetime.now(UTC)))
        s.commit()
    return str(uid)


def test_role_permissions_are_least_privilege():
    assert permissions(["analyst"]) == {"metrics.read", "health.read"}
    assert "users.manage" not in permissions(["security", "analyst", "content"])
    assert permissions(["superadmin"]) == set().union(*ROLES.values())
    assert "roles.manage" in ROLES["superadmin"] and all(
        "roles.manage" not in v for k, v in ROLES.items() if k != "superadmin"
    )


def test_non_admins_see_nothing(client):
    ada = signup(client)
    for path in ("/me", "/users", "/metrics", "/content", "/audit", "/health"):
        assert client.get(f"{A}{path}", headers=ada).status_code == 404
        assert client.get(f"{A}{path}").status_code == 401
    # An analyst can read metrics but not users or the audit log.
    _grant(client, ada, "analyst")
    assert client.get(f"{A}/me", headers=ada).json()["roles"] == ["analyst"]
    assert client.get(f"{A}/metrics", headers=ada).status_code == 200
    assert client.get(f"{A}/health", headers=ada).json()["database"] is True
    for path in ("/users", "/audit", "/content"):
        assert client.get(f"{A}{path}", headers=ada).status_code == 404


def test_support_tools_are_audited_and_never_show_private_content(client):
    sam = signup(client, "sam@example.com")
    _grant(client, sam, "support")
    client.cookies.clear()
    ada = signup(client)
    ada_id = _uid(client, ada)
    _big_five(client, ada)
    client.post(R, headers=ada)
    client.post("/api/v1/journal/entries", json={"body": "my private-zebra thoughts"}, headers=ada)
    use(client, Scripted(["Private coaching-giraffe reply."]))
    conv = new_conversation(client, ada)
    send(client, ada, conv["id"], "my coaching-giraffe question")

    found = client.get(f"{A}/users", params={"q": "ada@"}, headers=sam).json()["users"]
    assert [u["email"] for u in found] == ["ada@example.com"] and found[0]["plan_id"] == "free"
    assert client.get(f"{A}/users", params={"q": ada_id}, headers=sam).json()["users"][0]["id"] == ada_id
    assert client.get(f"{A}/users", params={"q": "%"}, headers=sam).json()["users"] == []
    detail = client.get(f"{A}/users/{ada_id}", headers=sam)
    assert detail.json()["completed_assessments"] == 1 and detail.json()["reports"] == 1
    for secret in ("private-zebra", "coaching-giraffe", "answers", "body"):
        assert secret not in detail.text
    assert client.get(f"{A}/users/{uuid.uuid4()}", headers=sam).status_code == 404

    # Complimentary Premium, then revoke it.
    r = client.post(
        f"{A}/users/{ada_id}/grants",
        json={"plan_id": "premium-monthly", "days": 30, "reason": "Outage"},
        headers=sam,
    )
    assert r.status_code == 200 and r.json()["plan_id"] == "premium-monthly"
    sub = r.json()["subscriptions"][0]
    assert sub["provider"] == "manual" and sub["cancel_at_period_end"] is True
    me = client.get("/api/v1/billing/me", headers=ada).json()
    assert me["plan_id"] == "premium-monthly" and not me["manage_available"]
    r = client.delete(f"{A}/users/{ada_id}/grants/{sub['id']}", headers=sam)
    assert r.json()["plan_id"] == "free"

    # Disable signs the person out and blocks sign-in; enable restores it.
    assert (
        client.post(
            f"{A}/users/{ada_id}/status", json={"status": "disabled", "reason": "x"}, headers=sam
        ).status_code
        == 422
    )
    r = client.post(
        f"{A}/users/{ada_id}/status", json={"status": "disabled", "reason": "Abuse report"}, headers=sam
    )
    assert r.json()["status"] == "disabled"
    assert client.get("/api/v1/auth/me", headers=ada).status_code == 401
    login = {"email": "ada@example.com", "password": PASSWORD}
    assert client.post("/api/v1/auth/login", json=login).status_code != 200
    client.post(f"{A}/users/{ada_id}/status", json={"status": "active", "reason": "Resolved"}, headers=sam)
    assert client.post("/api/v1/auth/login", json=login).status_code == 200
    sam_id = _uid(client, sam)
    r = client.post(f"{A}/users/{sam_id}/status", json={"status": "disabled", "reason": "oops"}, headers=sam)
    assert r.status_code == 409

    # Support can't manage roles or read the audit log.
    assert client.post(f"{A}/users/{ada_id}/roles", json={"role": "support"}, headers=sam).status_code == 404
    assert client.get(f"{A}/audit", headers=sam).status_code == 404

    with db(client) as s:
        events = [e for e in s.scalars(select(AuditEvent)) if e.event_type.startswith("admin.")]
    kinds = sorted(e.event_type for e in events)
    assert kinds == [
        "admin.subscription_granted",
        "admin.subscription_revoked",
        "admin.user_active",
        "admin.user_disabled",
    ]
    assert all(e.details["admin_id"] == sam_id for e in events)


def test_superadmin_roles_audit_metrics_and_content(client):
    root = signup(client, "root@example.com")
    root_id = _grant(client, root, "superadmin")
    client.cookies.clear()
    ada = signup(client)
    ada_id = _uid(client, ada)
    _big_five(client, ada)
    client.post(R, headers=ada)
    client.post("/api/v1/journal/entries", json={"body": "secret"}, headers=ada)

    r = client.post(f"{A}/users/{ada_id}/roles", json={"role": "analyst"}, headers=root)
    assert r.json()["admin_roles"] == ["analyst"]
    assert client.get(f"{A}/metrics", headers=ada).status_code == 200
    assert client.delete(f"{A}/users/{ada_id}/roles/analyst", headers=root).json()["admin_roles"] == []
    assert client.get(f"{A}/metrics", headers=ada).status_code == 404
    assert client.delete(f"{A}/users/{root_id}/roles/superadmin", headers=root).status_code == 409

    m = client.get(f"{A}/metrics", headers=root).json()
    assert m["users"]["total"] == 2 and m["users"]["last_7_days"] == 2 and m["verified_users"] == 2
    assert m["completed_assessments"]["total"] == 1 and m["assessments_by_instrument"] == {"mini-ipip-20": 1}
    assert m["reports_created"]["total"] == 1 and m["feature_users"]["journal"] == 1
    assert m["estimated_monthly_revenue_cents"] == 0 and m["coach_cost_30_days_usd"] is None
    assert "PDNA_AI_COST" in m["cost_note"]

    c = client.get(f"{A}/content", headers=root).json()
    assert {i["id"] for i in c["instruments"]} >= {"mini-ipip-20", "ipip-bfm-50"}
    assert all(len(f["sha256"]) == 64 for f in c["files"]) and c["engine_version"]

    log = client.get(f"{A}/audit", params={"event_type": "admin.", "limit": 1}, headers=root).json()
    assert len(log["items"]) == 1 and log["next_before"]
    more = client.get(
        f"{A}/audit", params={"event_type": "admin.", "before": log["next_before"]}, headers=root
    )
    assert {i["event_type"] for i in log["items"] + more.json()["items"]} == {
        "admin.role_granted",
        "admin.role_removed",
    }


def test_revenue_and_ai_cost_estimates(db_url):
    s = Settings(
        environment="test",
        database_url=db_url,
        content_dir=CONTENT_DIR,
        ai_cost_input_usd_per_mtok=5.0,
        ai_cost_output_usd_per_mtok=25.0,
        billing_dev_checkout=True,
    )
    from fastapi.testclient import TestClient

    with TestClient(create_app(s, create_schema=True)) as client:
        root = signup(client, "root@example.com")
        _grant(client, root, "analyst")
        client.cookies.clear()
        ada = signup(client)
        _big_five(client, ada)
        use(client, Scripted(["Hello."]))
        conv = new_conversation(client, ada)
        send(client, ada, conv["id"], "hi")
        client.post("/api/v1/billing/checkout", json={"plan_id": "premium-annual"}, headers=ada)
        m = client.get(f"{A}/metrics", headers=root).json()
        # Scripted provider: 100 input and 20 output tokens -> (100*5 + 20*25) / 1e6 dollars.
        assert m["coach_tokens_30_days"]["input"] == 100 and m["coach_tokens_30_days"]["output"] == 20
        assert m["coach_cost_30_days_usd"] == 0.0 and m["coach_active_users_30_days"] == 1
        # Development checkouts are not revenue.
        assert (
            m["active_subscriptions_by_provider"] == {"dev": 1} and m["estimated_monthly_revenue_cents"] == 0
        )


def test_grant_admin_command_line(client, monkeypatch, capsys):
    ada = signup(client)
    monkeypatch.setenv("PDNA_DATABASE_URL", str(client.app.state.settings.database_url))
    assert grant_cli(["ADA@example.com", "support"]) == 0
    assert client.get(f"{A}/me", headers=ada).json()["roles"] == ["support"]
    assert grant_cli(["ada@example.com", "support", "--remove"]) == 0
    assert client.get(f"{A}/me", headers=ada).status_code == 404
    assert grant_cli(["nobody@example.com", "support"]) == 1
    with pytest.raises(SystemExit):
        grant_cli(["ada@example.com", "owner"])
    with db(client) as s:
        assert s.scalar(select(User).where(User.email == "ada@example.com")) is not None
