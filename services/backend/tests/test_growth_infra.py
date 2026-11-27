"""Growth infrastructure: referral links and attribution, anonymous event counts, notifications and
reminders that never quote private content."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.database.models import Acquisition, AssessmentSession, Notification, ProductEventCount
from tests.conftest import start
from tests.test_admin import A, _grant
from tests.test_auth import PASSWORD, outbox, register, signup, token_from
from tests.test_relationships import CONSENT as REL_CONSENT
from tests.test_relationships import _invite

N = "/api/v1/notifications"


def test_referral_link_and_attribution(client):
    ada = signup(client)
    me = client.get("/api/v1/referrals/me", headers=ada).json()
    assert me["link"].endswith(f"/?ref={me['code']}") and me["joined"] == 0 and "never who" in me["note"]
    assert client.get("/api/v1/referrals/me", headers=ada).json()["code"] == me["code"]  # stable

    attribution = {"referral": me["code"], "source": "newsletter", "campaign": "spring"}
    assert register(client, "bob@example.com", attribution=attribution).status_code == 202
    assert client.get("/api/v1/referrals/me", headers=ada).json()["joined"] == 0  # not verified yet
    client.post(
        "/api/v1/auth/verify-email", json={"token": token_from(client, "bob@example.com", "verify_email")}
    )
    r = client.get("/api/v1/referrals/me", headers=ada)
    assert r.json()["joined"] == 1 and "bob@" not in r.text

    # Unknown codes are ignored; malformed tags are rejected.
    assert register(client, "cy@example.com", attribution={"referral": "zzzzzzzz"}).status_code == 202
    assert register(client, "di@example.com", attribution={"source": "Bad Tag!"}).status_code == 422
    with client.app.state.db.sessionmaker() as s:
        rows = {a.source: a.referrer_id is not None for a in s.scalars(select(Acquisition))}
    assert rows == {"newsletter": True}

    root = signup(client, "root@example.com")
    _grant(client, root, "analyst")
    m = client.get(f"{A}/metrics", headers=root).json()
    assert m["referred_signups_30_days"] == 1 and m["signups_by_source_30_days"] == {"newsletter": 1}


def test_anonymous_event_counts(client):
    for name in ("landing_view", "landing_view", "pricing_view", "made_up", "landing_view"):
        assert client.post("/api/v1/analytics/events", json={"name": name}).status_code == 204
    with client.app.state.db.sessionmaker() as s:
        counts = {r.name: r.count for r in s.scalars(select(ProductEventCount))}
        columns = set(ProductEventCount.__table__.columns.keys())
    assert counts == {"landing_view": 3, "pricing_view": 1}
    assert columns == {"day", "name", "count"}  # nothing that identifies anyone
    root = signup(client, "root@example.com")
    _grant(client, root, "analyst")
    assert client.get(f"{A}/metrics", headers=root).json()["product_events_30_days"]["landing_view"] == 3


def test_notifications_and_preferences(client):
    ada = signup(client)
    client.patch("/api/v1/me", json={"display_name": "Ada"}, headers=ada)
    token = _invite(client, ada)["token"]
    client.cookies.clear()
    bob = signup(client, "bob@example.com")
    client.patch("/api/v1/me", json={"display_name": "Bob"}, headers=bob)
    accept = {"token": token, "consent": REL_CONSENT}
    assert (
        client.post("/api/v1/relationships/invitations/accept", json=accept, headers=bob).status_code == 201
    )

    page = client.get(N, headers=ada).json()
    assert page["unread"] == 1 and page["notifications"][0]["title"] == "Bob accepted your invitation"
    assert page["notifications"][0]["link"].startswith("/relationships/")
    assert [m.kind for m in outbox(client, "ada@example.com")][-1] == "notify_relationships"
    assert client.get(N, headers=bob).json()["unread"] == 0  # nobody else sees it

    nid = page["notifications"][0]["id"]
    assert client.post(f"{N}/{nid}/read", headers=bob).status_code == 404
    assert client.post(f"{N}/{nid}/read", headers=ada).status_code == 204
    assert client.get(N, headers=ada).json()["unread"] == 0

    prefs = {p["kind"]: p for p in client.get(f"{N}/preferences", headers=ada).json()}
    assert prefs["security"]["required"] and not prefs["news"]["in_app"] and not prefs["news"]["email"]
    off = {"kind": "security", "in_app": True, "email": False}
    assert client.put(f"{N}/preferences", json=off, headers=ada).status_code == 409
    assert client.put(f"{N}/preferences", json={**off, "kind": "nope"}, headers=ada).status_code == 422
    r = client.put(
        f"{N}/preferences", json={"kind": "relationships", "in_app": False, "email": False}, headers=ada
    )
    assert {p["kind"]: p["in_app"] for p in r.json()}["relationships"] is False

    # With in-app and email off, a second acceptance creates nothing.
    token = _invite(client, ada, "friend")["token"]
    client.cookies.clear()
    cy = signup(client, "cy@example.com")
    sent = len(outbox(client, "ada@example.com"))
    client.post("/api/v1/relationships/invitations/accept", json={**accept, "token": token}, headers=cy)
    assert client.get(N, headers=ada).json()["notifications"][0]["title"] == "Bob accepted your invitation"
    assert len(outbox(client, "ada@example.com")) == sent
    assert client.post(f"{N}/read-all", headers=ada).status_code == 204

    export = client.get("/api/v1/privacy/export", headers=ada).json()
    assert export["notification_preferences"]["relationships"] == {"in_app": False, "email": False}
    assert len(export["notifications"]) == 1


def test_daily_reminders_are_generic_and_sent_once(client):
    ada = signup(client)
    sid, token_h, _ = start(client)
    client.post(
        "/api/v1/me/assessment-sessions/claim",
        json={"session_id": sid, "resume_token": token_h["X-Session-Token"]},
        headers=ada,
    )
    client.post("/api/v1/habits", json={"title": "Private habit title"}, headers=ada)
    client.post("/api/v1/growth/programs/focus-7/enrollment", headers=ada)
    with client.app.state.db.sessionmaker() as s:
        s.execute(update(AssessmentSession).values(updated_at=datetime.now(UTC) - timedelta(days=2)))
        s.commit()

    svc = client.app.state.notifications
    with client.app.state.db.sessionmaker() as s:
        assert svc.send_reminders(s) == {"assessment": 1, "development": 1, "goals": 1}
        assert svc.send_reminders(s) == {"assessment": 0, "development": 0, "goals": 0}
        notes = list(s.scalars(select(Notification)))
    titles = sorted(n.title for n in notes)
    assert titles == [
        "Day 1 of your programme is ready",
        "You planned 1 habit for today",
        "Your assessment is waiting",
    ]
    assert all("Private habit title" not in n.title + n.body for n in notes)
    # Reminder emails are off by default.
    assert not [m for m in outbox(client, "ada@example.com") if m.kind.startswith("notify_")]
    assert (
        client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD}).status_code
        == 200
    )
