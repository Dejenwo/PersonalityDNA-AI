import re
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select, update

from app.core.config import Settings
from app.database.models import AssessmentSession, AuthToken, ConsentRecord, RefreshToken, User
from app.security.consent import CURRENT_POLICY_VERSION
from tests.conftest import start

PASSWORD = "correct horse battery staple"
CSRF = {"X-PDNA-CSRF": "1"}


def register(client, email="ada@example.com", password=PASSWORD, **over):
    body = {
        "email": email,
        "password": password,
        "display_name": "Ada",
        "accepted_terms": True,
        "age_confirmed_18_plus": True,
        "policy_version": CURRENT_POLICY_VERSION,
        **over,
    }
    return client.post("/api/v1/auth/register", json=body)


def outbox(client, to=None):
    return client.app.state.email.messages(to)


def token_from(client, email, kind):
    msg = [m for m in outbox(client, email) if m.kind == kind][-1]
    return re.search(r"#token=([\w-]+)", msg.text).group(1)


def signup(client, email="ada@example.com"):
    assert register(client, email).status_code == 202
    assert (
        client.post(
            "/api/v1/auth/verify-email", json={"token": token_from(client, email, "verify_email")}
        ).status_code
        == 200
    )
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def db(client):
    return client.app.state.db.sessionmaker()


def test_register_verify_login_me(client):
    r = register(client, email="Ada@Example.com")
    assert r.status_code == 202
    msgs = outbox(client, "ada@example.com")
    assert [m.kind for m in msgs] == ["verify_email"]
    assert "http://localhost:3000/verify-email#token=" in msgs[0].text

    r = client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_unverified"

    tok = token_from(client, "ada@example.com", "verify_email")
    r = client.post("/api/v1/auth/verify-email", json={"token": tok})
    assert r.json()["email_verified"] is True
    # Single use.
    assert client.post("/api/v1/auth/verify-email", json={"token": tok}).status_code == 400

    r = client.post("/api/v1/auth/login", json={"email": "ADA@example.com", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["refresh_token"] is None  # web clients get a cookie instead
    cookie = r.headers["set-cookie"]
    assert "pdna_refresh=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "Path=/api/v1/auth" in cookie
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
    assert me["email"] == "ada@example.com" and me["display_name"] == "Ada"
    with db(client) as s:
        user = s.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        consent = s.scalar(select(ConsentRecord).where(ConsentRecord.user_id == user.id))
        assert consent.consent_type == "account_terms_privacy"


def test_registration_does_not_reveal_existing_accounts(client):
    signup(client)
    r1 = register(client, "ada@example.com")
    r2 = register(client, "new@example.com")
    assert r1.status_code == r2.status_code == 202 and r1.json() == r2.json()
    assert outbox(client, "ada@example.com")[-1].kind == "already_registered"
    with db(client) as s:
        assert len(s.scalars(select(User)).all()) == 2


@pytest.mark.parametrize(
    "over,code",
    [
        ({"password": "short"}, "weak_password"),
        ({"password": "password123"}, "weak_password"),
        ({"password": "aaaaaaaaaaaa"}, "weak_password"),
        ({"accepted_terms": False}, "consent_required"),
        ({"age_confirmed_18_plus": False}, "age_requirement"),
        ({"policy_version": "old"}, "consent_outdated"),
    ],
)
def test_registration_validation(client, over, code):
    r = register(client, **over)
    assert r.json()["error"]["code"] == code
    assert outbox(client) == []


def test_invalid_email_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_bad_credentials_are_generic(client):
    signup(client)
    wrong = client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "wrong password!"}
    )
    missing = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong password!"}
    )
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_refresh_rotation_and_reuse_detection(client):
    signup(client)
    first = client.cookies.get("pdna_refresh")
    assert client.post("/api/v1/auth/refresh").status_code == 403  # CSRF header required for cookie refresh
    r = client.post("/api/v1/auth/refresh", headers=CSRF)
    assert r.status_code == 200 and r.json()["access_token"]
    second = client.cookies.get("pdna_refresh")
    assert second and second != first

    # Replaying the rotated token revokes the whole family, including the newest token.
    client.cookies.clear()
    client.cookies.set("pdna_refresh", first)
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401
    client.cookies.clear()
    client.cookies.set("pdna_refresh", second)
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_mobile_refresh_in_body_and_logout(client):
    signup(client)
    r = client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD, "client": "mobile"}
    )
    rt = r.json()["refresh_token"]
    assert rt
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200
    new_rt = r.json()["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": new_rt}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": new_rt}).status_code == 401


def test_password_reset_flow(client):
    headers = signup(client)
    assert (
        client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}).status_code
        == 202
    )
    assert outbox(client, "nobody@example.com") == []
    client.post("/api/v1/auth/password-reset/request", json={"email": "ada@example.com"})
    tok = token_from(client, "ada@example.com", "reset_password")

    # A weak password does not burn the token.
    r = client.post("/api/v1/auth/password-reset/confirm", json={"token": tok, "password": "short"})
    assert r.json()["error"]["code"] == "weak_password"

    # Access tokens issued before the change stop working.
    with db(client) as s:
        uid = s.scalar(select(User)).id
    old_access, _ = client.app.state.access_tokens.issue(uid, now=datetime.now(UTC) - timedelta(seconds=30))

    new_password = "a completely new passphrase"
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm", json={"token": tok, "password": new_password}
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm", json={"token": tok, "password": new_password}
        ).status_code
        == 400
    )
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_access}"}).status_code == 401
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401  # sessions revoked
    assert (
        client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD}).status_code
        == 401
    )
    r = client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": new_password})
    assert r.status_code == 200
    assert headers  # original fixture header used above via old_access


def test_expired_and_wrong_purpose_tokens(client):
    register(client)
    tok = token_from(client, "ada@example.com", "verify_email")
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm", json={"token": tok, "password": "another long pass"}
        ).status_code
        == 400
    )
    with db(client) as s:
        s.execute(update(AuthToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
        s.commit()
    assert client.post("/api/v1/auth/verify-email", json={"token": tok}).status_code == 400
    # Resend issues a fresh, working link and invalidates older ones.
    client.post("/api/v1/auth/resend-verification", json={"email": "ada@example.com"})
    fresh = token_from(client, "ada@example.com", "verify_email")
    assert fresh != tok
    assert client.post("/api/v1/auth/verify-email", json={"token": fresh}).status_code == 200


def test_invalid_bearer_is_rejected_not_ignored(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = {"Authorization": "Bearer not.a.jwt"}
    assert client.get("/api/v1/auth/me", headers=bad).status_code == 401
    assert client.get("/api/v1/assessments").status_code == 200
    r = client.post(
        "/api/v1/assessment-sessions",
        headers=bad,
        json={
            "instrument_id": "mini-ipip-20",
            "consent": {
                "accepted": True,
                "age_confirmed_18_plus": True,
                "policy_version": CURRENT_POLICY_VERSION,
            },
        },
    )
    assert r.status_code == 401


def _complete(client, sid, h):
    items = client.get("/api/v1/assessments/mini-ipip-20").json()["items"]
    client.put(
        f"/api/v1/assessment-sessions/{sid}/answers",
        json={"answers": [{"item_id": i["id"], "value": (n % 5) + 1} for n, i in enumerate(items)]},
        headers=h,
    )
    return client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h).json()["id"]


def test_claim_history_and_owner_access(client):
    sid, token_h, _ = start(client)
    rid = _complete(client, sid, token_h)
    ada = signup(client)
    r = client.post(
        "/api/v1/me/assessment-sessions/claim",
        json={"session_id": sid, "resume_token": token_h["X-Session-Token"]},
        headers=ada,
    )
    assert r.status_code == 200 and r.json()["result_id"] == rid
    # Owner can read without the device token.
    assert client.get(f"/api/v1/results/{rid}", headers=ada).status_code == 200
    hist = client.get("/api/v1/personality/history", headers=ada).json()["items"]
    assert [(h["session_id"], h["status"], h["answered"], h["total"]) for h in hist] == [
        (sid, "completed", 20, 20)
    ]

    # Another account cannot claim or read it, even with a valid bearer.
    client.cookies.clear()
    bob = signup(client, "bob@example.com")
    r = client.post(
        "/api/v1/me/assessment-sessions/claim",
        json={"session_id": sid, "resume_token": token_h["X-Session-Token"]},
        headers=bob,
    )
    assert r.status_code == 404
    assert client.get(f"/api/v1/results/{rid}", headers=bob).status_code == 404
    assert client.get("/api/v1/personality/history", headers=bob).json()["items"] == []


def test_signed_in_session_is_owned(client):
    ada = signup(client)
    r = client.post(
        "/api/v1/assessment-sessions",
        headers=ada,
        json={
            "instrument_id": "ipip-bfm-50",
            "consent": {
                "accepted": True,
                "age_confirmed_18_plus": True,
                "policy_version": CURRENT_POLICY_VERSION,
            },
        },
    )
    sid = r.json()["session"]["id"]
    hist = client.get("/api/v1/personality/history", headers=ada).json()["items"]
    assert hist[0]["session_id"] == sid and hist[0]["status"] == "in_progress" and hist[0]["total"] == 50
    assert client.get(f"/api/v1/assessment-sessions/{sid}", headers=ada).status_code == 200


def test_update_profile(client):
    ada = signup(client)
    r = client.patch("/api/v1/me", json={"display_name": "  Ada L.  "}, headers=ada)
    assert r.json()["display_name"] == "Ada L."
    assert client.patch("/api/v1/me", json={"email": "x@example.com"}, headers=ada).status_code == 422


def test_export_and_delete_account(client):
    ada = signup(client)
    sid, h, _ = start(client)
    rid = _complete(client, sid, h)
    client.post(
        "/api/v1/me/assessment-sessions/claim",
        json={"session_id": sid, "resume_token": h["X-Session-Token"]},
        headers=ada,
    )

    data = client.get("/api/v1/privacy/export", headers=ada).json()
    assert data["account"]["email"] == "ada@example.com"
    assert {c["type"] for c in data["consents"]} == {"account_terms_privacy", "assessment_processing"}
    a = data["assessments"][0]
    assert len(a["answers"]) == 20 and a["answers"][0]["statement"]
    assert a["result"]["id"] == rid

    assert (
        client.request(
            "DELETE", "/api/v1/account", json={"password": "wrong password!"}, headers=ada
        ).status_code
        == 403
    )
    assert (
        client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada).status_code
        == 204
    )
    # Everything linked is gone, even for the device token.
    assert client.get(f"/api/v1/results/{rid}", headers=h).status_code == 404
    assert client.get("/api/v1/auth/me", headers=ada).status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD}).status_code
        == 401
    )
    with db(client) as s:
        assert s.scalars(select(AssessmentSession)).all() == []
        assert s.scalars(select(RefreshToken)).all() == []
        # Consent proof is kept, unlinked.
        assert all(c.user_id is None for c in s.scalars(select(ConsentRecord)))


def test_login_rate_limited(settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings.auth_rate_limit = 3
    with TestClient(create_app(settings, create_schema=True)) as c:
        codes = [
            c.post(
                "/api/v1/auth/login", json={"email": "x@example.com", "password": "whatever pass"}
            ).status_code
            for _ in range(4)
        ]
    assert codes == [401, 401, 401, 429]


def test_dev_outbox_endpoint_only_when_enabled(settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app(settings, create_schema=True)) as c:
        assert c.get("/api/v1/dev/outbox").status_code == 404
    settings.dev_outbox_endpoint = True
    with TestClient(create_app(settings, create_schema=True)) as c:
        register(c)
        assert (
            c.get("/api/v1/dev/outbox", params={"to": "ada@example.com"}).json()["items"][0]["kind"]
            == "verify_email"
        )


@pytest.mark.parametrize(
    "over,match",
    [
        ({}, "JWT_SECRET"),
        ({"jwt_secret": "x" * 40}, "outbox"),
        (
            {"jwt_secret": "x" * 40, "email_provider": "smtp", "smtp_host": "smtp.example.com"},
            "COOKIE_SECURE",
        ),
        (
            {
                "jwt_secret": "x" * 40,
                "email_provider": "smtp",
                "smtp_host": "h",
                "refresh_cookie_secure": True,
            },
            "SQLite",
        ),
    ],
)
def test_production_settings_guards(over, match):
    with pytest.raises(ValidationError, match=match):
        Settings(environment="production", **over)
