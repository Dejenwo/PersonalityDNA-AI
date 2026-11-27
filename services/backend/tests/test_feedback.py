"""Beta feedback: sending signed in or out, encryption at rest, support triage, privacy and limits."""

from sqlalchemy import select

from app.database.models import AuditEvent, Feedback
from app.security.retention import purge_expired
from tests.test_admin import _grant, _uid
from tests.test_auth import db, signup

F = "/api/v1/feedback"
ADMIN = "/api/v1/admin/feedback"


def test_anonymous_feedback_is_encrypted_and_keeps_only_the_path(client):
    r = client.post(
        F,
        json={
            "kind": "bug",
            "message": "  The next button does nothing on question 7.  ",
            "page": "/assessment/abc?token=secret-value#x",
            "app_version": "web-1.0",
            "contact_ok": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["message"] == "The next button does nothing on question 7."
    assert body["page"] == "/assessment/abc" and body["status"] == "new"
    with db(client) as s:
        row = s.scalars(select(Feedback)).one()
        assert row.user_id is None and row.contact_ok is False  # signed out can't be contacted
        assert "next button" not in row.message_encrypted and row.message_encrypted.startswith("v1:")


def test_bad_input_is_rejected(client):
    assert client.post(F, json={"kind": "bug", "message": "   short    "}).status_code == 422
    assert client.post(F, json={"kind": "rant", "message": "A long enough message"}).status_code == 422
    assert client.post(F, json={"kind": "idea", "message": "x" * 2001}).status_code == 422
    r = client.post(
        F, json={"kind": "idea", "message": "A long enough message", "page": "https://evil.example"}
    )
    assert r.status_code == 201 and r.json()["page"] is None


def test_people_see_their_own_feedback_only(client):
    ada, bob = signup(client), signup(client, "bob@example.com")
    client.post(F, json={"kind": "idea", "message": "Dark mode for the PDF please"}, headers=ada)
    mine = client.get(F, headers=ada).json()["items"]
    assert [i["message"] for i in mine] == ["Dark mode for the PDF please"]
    assert client.get(F, headers=bob).json()["items"] == []
    assert client.get(F).status_code == 401
    export = client.get("/api/v1/privacy/export", headers=ada).json()
    assert [f["message"] for f in export["feedback"]] == ["Dark mode for the PDF please"]


def test_support_triages_and_sees_the_account_only_with_permission_to_contact(client):
    ada, bob = signup(client), signup(client, "bob@example.com")
    client.post(
        F, json={"kind": "content", "message": "Typo on the careers page", "contact_ok": True}, headers=ada
    )
    client.post(F, json={"kind": "bug", "message": "Chart overlaps on my phone"}, headers=bob)
    client.post(F, json={"kind": "other", "message": "Anonymous note for the team"})

    support = signup(client, "support@example.com")
    assert client.get(ADMIN, headers=support).status_code == 404  # not an admin yet
    _grant(client, support, "analyst")
    assert client.get(ADMIN, headers=support).status_code == 404  # wrong role
    _grant(client, support, "support")

    data = client.get(ADMIN, headers=support).json()
    assert data["counts"] == {"new": 3, "planned": 0, "fixed": 0, "closed": 0}
    by_msg = {i["message"]: i for i in data["items"]}
    assert by_msg["Typo on the careers page"]["user_id"] == _uid(client, ada)
    assert by_msg["Chart overlaps on my phone"]["user_id"] is None
    assert by_msg["Chart overlaps on my phone"]["signed_in"] is True
    assert by_msg["Anonymous note for the team"]["signed_in"] is False

    fid = by_msg["Chart overlaps on my phone"]["id"]
    r = client.post(f"{ADMIN}/{fid}/status", json={"status": "fixed"}, headers=support)
    assert r.status_code == 200 and r.json()["status"] == "fixed"
    assert client.get(F, headers=bob).json()["items"][0]["status"] == "fixed"
    only_bugs = client.get(ADMIN, params={"kind": "bug", "status": "fixed"}, headers=support).json()
    assert [i["id"] for i in only_bugs["items"]] == [fid]
    page = client.get(ADMIN, params={"limit": 2}, headers=support).json()
    assert len(page["items"]) == 2 and page["next_before"] is not None
    with db(client) as s:
        ev = s.scalars(select(AuditEvent).where(AuditEvent.event_type == "admin.feedback_status")).one()
        assert ev.details["new"] == "fixed" and "Chart" not in str(ev.details)

    assert (
        client.post(f"{ADMIN}/not-a-uuid/status", json={"status": "fixed"}, headers=support).status_code
        == 404
    )
    content = signup(client, "content@example.com")
    _grant(client, content, "content")  # may read, may not change
    assert client.get(ADMIN, headers=content).status_code == 200
    assert client.post(f"{ADMIN}/{fid}/status", json={"status": "new"}, headers=content).status_code == 404


def test_rate_limit_and_retention(client):
    ada = signup(client)
    for _ in range(10):
        assert (
            client.post(F, json={"kind": "idea", "message": "One more small idea"}, headers=ada).status_code
            == 201
        )
    r = client.post(F, json={"kind": "idea", "message": "One more small idea"}, headers=ada)
    assert r.status_code == 429
    from datetime import UTC, datetime, timedelta

    with db(client) as s:
        assert purge_expired(s, now=datetime.now(UTC) + timedelta(days=366))["feedback"] == 10
