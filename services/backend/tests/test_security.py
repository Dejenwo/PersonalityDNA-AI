"""Security sweeps over the whole API: every private route needs sign-in, nobody reaches another person's
records by id, nothing answers with a server error, and private content never reaches the logs."""

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from app.database.base import Base
from app.database.models import (
    AssessmentSession,
    AuthToken,
    OrgInvitation,
    RefreshToken,
    RelationshipInvitation,
    User,
)
from app.security.retention import purge_expired
from tests.conftest import start
from tests.test_auth import CSRF, PASSWORD, outbox, signup, token_from
from tests.test_coach import CONSENT as COACH_CONSENT
from tests.test_organizations import _org
from tests.test_relationships import _invite
from tests.test_reports import R, _big_five

# Routes anyone may call. Everything else must answer 401 without credentials.
PUBLIC = {
    ("GET", "/health"),
    ("GET", "/api/v1/assessments"),
    ("GET", "/api/v1/assessments/{instrument_id}"),
    ("GET", "/api/v1/billing/plans"),
    ("GET", "/api/v1/growth/programs"),
    ("GET", "/api/v1/growth/programs/{program_id}"),
    ("GET", "/api/v1/journal/prompts"),
    ("GET", "/api/v1/learning/{track_id}/modules"),
    ("GET", "/api/v1/learning/{track_id}/modules/{module_id}"),
    ("GET", "/api/v1/locales"),
    ("GET", "/api/v1/public/cards/{token}"),
    ("GET", "/api/v1/public/cards/{token}/image.svg"),
    ("POST", "/api/v1/analytics/events"),
    # Anonymous assessments are protected by the per-session resume token instead.
    ("POST", "/api/v1/assessment-sessions"),
    ("GET", "/api/v1/assessment-sessions/{session_id}"),
    ("PUT", "/api/v1/assessment-sessions/{session_id}/answers"),
    ("POST", "/api/v1/assessment-sessions/{session_id}/complete"),
    ("GET", "/api/v1/results/{result_id}"),
    # Account entry points.
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/verify-email"),
    ("POST", "/api/v1/auth/resend-verification"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/password-reset/request"),
    ("POST", "/api/v1/auth/password-reset/confirm"),
}

PARAM = re.compile(r"\{[^}]+\}")
MARKER = "zebra-private-marker"


def _operations(client):
    for path, ops in client.app.openapi()["paths"].items():
        for method in ops:
            yield method.upper(), path


def test_private_routes_need_sign_in(client):
    seen = set()
    for method, path in _operations(client):
        seen.add((method, path))
        r = client.request(method, PARAM.sub(str(uuid.uuid4()), path), json={})
        assert r.status_code < 500, (method, path, r.status_code)
        if (method, path) not in PUBLIC:
            assert r.status_code == 401, (method, path, r.status_code)
    assert seen >= PUBLIC, PUBLIC - seen  # the allowlist only names routes that exist


def _populate(client, h):
    """Gives one person one of nearly everything: results, report, card, journal, goal, habit, programme,
    coaching, relationship invitation, organisation, notification preference."""
    _big_five(client, h)
    rep = client.post(R, headers=h).json()
    assert client.post("/api/v1/share-cards", json={"report_id": rep["id"]}, headers=h).status_code == 201
    calls = [
        ("POST", "/api/v1/journal/entries", {"body": f"{MARKER} journal"}),
        ("POST", "/api/v1/goals", {"title": f"{MARKER} goal", "milestones": [{"title": "one"}]}),
        ("POST", "/api/v1/habits", {"title": f"{MARKER} habit"}),
        ("POST", "/api/v1/growth/programs/focus-7/enrollment", None),
        ("PUT", "/api/v1/notifications/preferences", {"kind": "news", "in_app": True, "email": False}),
    ]
    for method, path, body in calls:
        r = client.request(method, path, json=body, headers=h)
        assert r.status_code < 300, (path, r.text)
    cid = client.post("/api/v1/coach/conversations", json={"consent": COACH_CONSENT}, headers=h).json()["id"]
    r = client.post(
        f"/api/v1/coach/conversations/{cid}/messages", json={"content": f"{MARKER} coach"}, headers=h
    )
    assert r.status_code == 200, r.text
    _invite(client, h)
    org = _org(client, h)
    r = client.post(f"/api/v1/orgs/{org['id']}/invitations", json={"role": "member"}, headers=h)
    assert r.status_code == 201, r.text


def _row_ids(client) -> set[str]:
    """One id per table, from every UUID column of its first row."""
    ids: set[str] = set()
    with client.app.state.db.sessionmaker() as s:
        for table in Base.metadata.sorted_tables:
            row = s.execute(select(table).limit(1)).mappings().first()
            for value in (row or {}).values():
                if isinstance(value, uuid.UUID):
                    ids.add(str(value))
    return ids


def test_nobody_reaches_another_persons_records_by_id(client):
    ada = signup(client)
    _populate(client, ada)
    ids = _row_ids(client)
    assert len(ids) > 20
    client.cookies.clear()
    eve = signup(client, "eve@example.com")

    leaks = []
    for method, path in _operations(client):
        if (method, path) in PUBLIC or not PARAM.search(path):
            continue
        for value in ids:
            r = client.request(method, PARAM.sub(value, path), json={}, headers=eve)
            assert r.status_code < 500, (method, path, r.status_code)
            if r.status_code < 300:
                leaks.append((method, path, r.status_code))
    assert leaks == []

    # Ada's records are untouched by the sweep.
    assert len(client.get("/api/v1/journal/entries", headers=ada).json()["items"]) == 1
    assert len(client.get("/api/v1/goals", headers=ada).json()["goals"]) == 1


def test_private_content_never_reaches_logs(client, caplog):
    # Other tests (Alembic's logging config) can disable existing loggers; capture everything here.
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.disabled = False
            logger.propagate = True
    caplog.set_level(logging.DEBUG)
    ada = signup(client)
    _populate(client, ada)
    client.post("/api/v1/journal/search", json={"q": MARKER}, headers=ada)
    client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert caplog.records, "logging is captured"
    assert MARKER not in caplog.text and PASSWORD not in caplog.text


def _points_at_users(column) -> bool:
    return any(fk.column.table.name == "users" for fk in column.foreign_keys)


def test_every_table_with_personal_data_is_removed_with_the_account(client):
    ada = signup(client)
    _populate(client, ada)
    with client.app.state.db.sessionmaker() as s:
        uid = s.scalar(select(User.id).where(User.email == "ada@example.com"))
    assert (
        client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada).status_code
        == 204
    )

    remaining = []
    with client.app.state.db.sessionmaker() as s:
        for table in Base.metadata.sorted_tables:
            for column in table.columns:
                if _points_at_users(column) and s.execute(select(table).where(column == uid)).first():
                    remaining.append(f"{table.name}.{column.name}")
    # The audit log keeps events as text ids (not a person column), as the record that deletion happened.
    assert remaining == [], remaining


def test_security_notices_for_password_change_and_stolen_sessions(client):
    ada = signup(client)
    first = client.cookies.get("pdna_refresh")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200
    client.cookies.clear()
    client.cookies.set("pdna_refresh", first)
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401  # replayed: all sessions end

    client.post("/api/v1/auth/password-reset/request", json={"email": "ada@example.com"})
    tok = token_from(client, "ada@example.com", "reset_password")
    new = "a different long passphrase"
    assert (
        client.post("/api/v1/auth/password-reset/confirm", json={"token": tok, "password": new}).status_code
        == 204
    )

    mails = [m for m in outbox(client, "ada@example.com") if m.kind == "notify_security"]
    assert [m.subject for m in mails] == ["We signed you out everywhere", "Your password was changed"]
    assert all(new not in m.text and tok not in m.text for m in mails)
    login = client.post("/api/v1/auth/login", json={"email": "ada@example.com", "password": new})
    ada = {"Authorization": f"Bearer {login.json()['access_token']}"}
    titles = [n["title"] for n in client.get("/api/v1/notifications", headers=ada).json()["notifications"]]
    assert set(titles) == {"We signed you out everywhere", "Your password was changed"}


def test_retention_purges_only_what_has_expired(client):
    ada = signup(client)
    _invite(client, ada)
    org = _org(client, ada)
    client.post(f"/api/v1/orgs/{org['id']}/invitations", json={"role": "member"}, headers=ada)
    old, _, _ = start(client)
    fresh, _, _ = start(client)
    now = datetime.now(UTC)
    with client.app.state.db.sessionmaker() as s:
        s.execute(
            update(AssessmentSession)
            .where(AssessmentSession.id == uuid.UUID(old))
            .values(updated_at=now - timedelta(days=31))
        )
        s.commit()
        assert purge_expired(s, now)["anonymous_unfinished_assessments"] == 1
        assert {str(i) for i in s.scalars(select(AssessmentSession.id))} == {fresh}

        # Nothing else has expired yet; a year later, tokens and invitations have.
        assert purge_expired(s, now)["refresh_tokens"] == 0
        later = purge_expired(s, now + timedelta(days=365))
        assert later["email_tokens"] >= 1 and later["refresh_tokens"] >= 1
        assert later["relationship_invitations"] == 1 and later["organisation_invitations"] == 1
        assert later["audit_events"] >= 1
        for model in (AuthToken, RefreshToken, RelationshipInvitation, OrgInvitation):
            assert s.scalar(select(func.count()).select_from(model)) == 0
        # Accounts and their claimed data are untouched.
        assert s.scalar(select(func.count()).select_from(User)) == 1


def test_api_security_headers(client, settings):
    r = client.get("/api/v1/locales")
    assert r.headers["content-security-policy"].startswith("default-src 'none'")
    assert r.headers["cross-origin-resource-policy"] == "same-site"
    assert r.headers["cross-origin-opener-policy"] == "same-origin"
    assert "strict-transport-security" not in r.headers  # only behind TLS
    assert client.get("/api/v1/public/cards/x").headers["cross-origin-resource-policy"] == "cross-origin"

    from fastapi.testclient import TestClient

    from app.main import create_app

    prod = settings.model_copy(update={"environment": "staging"})
    with TestClient(create_app(prod, create_schema=True)) as c:
        assert c.get("/health").headers["strict-transport-security"].startswith("max-age=")


def test_production_needs_https_origins_and_links():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    ok = {
        "environment": "production",
        "jwt_secret": "x" * 40,
        "email_provider": "smtp",
        "smtp_host": "smtp.example.com",
        "refresh_cookie_secure": True,
        "database_url": "postgresql+psycopg://u:p@db/pdna",
        "data_encryption_key": "A" * 43,
        "coach_enabled": False,
        "cors_origins": ["https://app.example.com"],
        "web_base_url": "https://app.example.com",
    }
    assert Settings(**ok).environment == "production"
    for bad, match in [
        ({"cors_origins": ["*"]}, "CORS_ORIGINS"),
        ({"cors_origins": ["http://app.example.com"]}, "CORS_ORIGINS"),
        ({"web_base_url": "http://app.example.com"}, "WEB_BASE_URL"),
    ]:
        with pytest.raises(ValidationError, match=match):
            Settings(**{**ok, **bad})
