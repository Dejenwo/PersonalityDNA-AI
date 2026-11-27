"""Personality reports: deterministic build, encrypted storage, ownership, PDF, export and deletion."""

import uuid

import pytest
from sqlalchemy import select

from app.assessments.content import load_content
from app.database.models import Report, User
from app.reports.builder import body_sha256, build_report
from app.reports.pdf import render_pdf
from app.reports.service import latest_results
from tests.conftest import CONTENT_DIR, start
from tests.test_auth import PASSWORD, _complete, db, signup
from tests.test_careers import INSTRUMENT as INTERESTS
from tests.test_careers import _take

R = "/api/v1/reports"


def _claim(client, h, sid, token_h):
    r = client.post(
        "/api/v1/me/assessment-sessions/claim",
        json={"session_id": sid, "resume_token": token_h["X-Session-Token"]},
        headers=h,
    )
    assert r.status_code == 200, r.text


def _big_five(client, h):
    sid, token_h, _ = start(client)
    rid = _complete(client, sid, token_h)
    _claim(client, h, sid, token_h)
    return rid


def _interests(client, h):
    sid, token_h, _ = start(client, INTERESTS)
    assert _take(client, {"sid": sid}, headers=token_h).status_code == 200
    _claim(client, h, sid, token_h)


def _user(client, h):
    me = client.get("/api/v1/auth/me", headers=h).json()
    s = db(client)
    return s, s.get(User, uuid.UUID(me["id"]))


def test_no_report_without_big_five(client):
    ada = signup(client)
    r = client.post(R, headers=ada)
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_results"
    assert client.get(R, headers=ada).json() == {"reports": []}
    assert client.get(R).status_code == 401


def test_build_is_deterministic_and_plan_is_grounded(client):
    ada = signup(client)
    _big_five(client, ada)
    bundle = load_content(CONTENT_DIR)
    s, user = _user(client, ada)
    with s:
        results = latest_results(s, bundle, user)
    assert set(results) == {"big_five"}
    a, b = build_report(bundle, results), build_report(bundle, results)
    assert a == b and body_sha256(a) == body_sha256(b)
    assert [src.kind for src in a.sources] == ["big_five"]
    assert len(a.traits) == 5 and all(t.score is not None for t in a.traits)
    # Every scored band has communication guidance from the versioned content.
    assert all(t.communication and t.relationships for t in a.traits)
    assert a.plan[0].id == "foundations-30" and a.plan[0].href == "/growth/foundations-30"
    assert len({p.id for p in a.plan}) == len(a.plan) <= 6
    assert len(a.strengths) <= 8 and len(a.development) <= 6
    assert a.interests is None and a.leadership is None
    assert a.limitations and a.methodology[0].kind == "big_five"
    with pytest.raises(ValueError):
        build_report(bundle, {})

    pdf = render_pdf(a, "27 November 2026")
    assert pdf.startswith(b"%PDF") and render_pdf(a, "27 November 2026")[:8] == pdf[:8]


def test_create_read_pdf_and_delete(client):
    ada = signup(client)
    rid = _big_five(client, ada)
    _interests(client, ada)
    r = client.post(R, headers=ada)
    assert r.status_code == 201, r.text
    rep = r.json()
    body = rep["body"]
    assert [s["kind"] for s in body["sources"]] == ["big_five", "interests"]
    assert body["sources"][0]["result_id"] == rid
    assert body["interests"]["code"] and len(body["interests"]["top"]) == 3
    assert "work-and-career-60" in [p["id"] for p in body["plan"]]
    assert body["profile"]["name"]

    lst = client.get(R, headers=ada).json()["reports"]
    assert [(x["id"], x["kinds"]) for x in lst] == [(rep["id"], ["big_five", "interests"])]
    assert lst[0]["headline"] == body["profile"]["name"]
    assert client.get(f"{R}/{rep['id']}", headers=ada).json() == rep

    pdf = client.get(f"{R}/{rep['id']}/pdf", headers=ada)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["cache-control"] == "no-store"
    assert 'attachment; filename="personality-report-' in pdf.headers["content-disposition"]

    # Stored encrypted: the profile name never appears in the database row.
    with db(client) as s:
        row = s.scalars(select(Report)).one()
        assert body["profile"]["summary"] not in row.body_encrypted
        assert row.body_encrypted.startswith("v1:") and row.body_sha256 == rep["sha256"]

    assert client.delete(f"{R}/{rep['id']}", headers=ada).status_code == 204
    assert client.get(f"{R}/{rep['id']}", headers=ada).status_code == 404
    assert client.get(f"{R}/not-a-uuid", headers=ada).status_code == 404


def test_reports_belong_to_their_owner(client):
    ada = signup(client)
    _big_five(client, ada)
    rep = client.post(R, headers=ada).json()
    client.cookies.clear()
    bob = signup(client, "bob@example.com")
    for path in (f"{R}/{rep['id']}", f"{R}/{rep['id']}/pdf"):
        assert client.get(path, headers=bob).status_code == 404
    assert client.delete(f"{R}/{rep['id']}", headers=bob).status_code == 404
    assert client.get(R, headers=bob).json() == {"reports": []}
    # Bob has no results of his own, so he cannot build one from Ada's.
    assert client.post(R, headers=bob).status_code == 409


def test_report_limit(client, monkeypatch):
    monkeypatch.setattr("app.reports.service.MAX_REPORTS", 2)
    ada = signup(client)
    _big_five(client, ada)
    assert client.post(R, headers=ada).status_code == 201
    assert client.post(R, headers=ada).status_code == 201
    r = client.post(R, headers=ada)
    assert r.status_code == 409 and r.json()["error"]["code"] == "too_many_reports"


def test_export_and_account_deletion(client):
    ada = signup(client)
    _big_five(client, ada)
    rep = client.post(R, headers=ada).json()
    exported = client.get("/api/v1/privacy/export", headers=ada).json()["reports"]
    assert exported == [rep]
    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204
    with db(client) as s:
        assert s.scalars(select(Report)).all() == []
