import json
import shutil
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.assessments.content import ContentError, load_content
from app.careers.interests import RIASEC, interest_profile
from app.coaching.context import facts_from_result, render_context
from app.core.config import Settings
from app.database.models import AssessmentResult
from app.main import create_app
from app.scoring.engine import ENGINE_VERSION, score
from tests.conftest import CONTENT_DIR, start
from tests.test_auth import _complete, db, signup
from tests.test_coach import CONSENT, Scripted, send, use

INSTRUMENT = "onet-ipsf-60"


# ---------- interest profile (pure) ----------


def test_profile_ranking_code_and_ties():
    p = interest_profile(
        {"realistic": 2, "investigative": 9, "artistic": 7, "social": 7, "enterprising": 1, "conventional": 0}
    )
    assert p.code == "IAS"
    assert p.ranking[0] == ("investigative", 9)
    assert p.boundary_ties == ()  # A and S are both inside the top three
    assert not p.empty


def test_profile_reports_ties_across_the_third_place():
    p = interest_profile(
        {"realistic": 5, "investigative": 8, "artistic": 5, "social": 5, "enterprising": 1, "conventional": 0}
    )
    # Holland order breaks the tie deterministically, and the tie is reported rather than hidden.
    assert p.code == "IRA"
    assert p.boundary_ties == ("realistic", "artistic", "social")


def test_profile_empty_and_invalid():
    assert interest_profile(dict.fromkeys(RIASEC, 0)).empty
    with pytest.raises(ValueError):
        interest_profile({"realistic": 1})


# ---------- scoring (hand-computed) ----------


def test_count_endorsed_scoring(content):
    inst = content.instrument(INSTRUMENT, "1.0.0").data
    # Investigative: 7 of 10 liked; all other areas: first 3 liked.
    answers = {}
    for area in RIASEC:
        items = [i for i in inst.items if i.scale == area]
        liked = 7 if area == "investigative" else 3
        for n, item in enumerate(items):
            answers[item.id] = 2 if n < liked else 1
    out = score(inst, answers)
    assert out.engine_version == ENGINE_VERSION == "1.1.0"
    by = {s.scale_id: s for s in out.scales}
    assert (by["investigative"].raw_mean, by["investigative"].score, by["investigative"].band) == (
        7.0,
        70.0,
        None,
    )
    assert (by["realistic"].raw_mean, by["realistic"].score) == (3.0, 30.0)
    assert out.complete


def test_every_item_is_required(content):
    inst = content.instrument(INSTRUMENT, "1.0.0").data
    answers = {i.id: 2 for i in inst.items[:-1]}
    out = score(inst, answers)
    assert {s.scale_id for s in out.scales if s.status == "insufficient"} == {"conventional"}


# ---------- content rules ----------


def test_instrument_structure(content):
    inst = content.instrument(INSTRUMENT, "1.0.0").data
    assert (inst.family, inst.scoring, inst.status) == ("interests", "count_endorsed", "draft")
    assert len(inst.items) == 60
    for area in RIASEC:
        assert sum(1 for i in inst.items if i.scale == area) == 10
    assert all(i.keyed == "+" for i in inst.items)
    assert inst.license.file == "licenses/ONET.md"


def test_drafts_are_excluded_when_disabled():
    bundle = load_content(CONTENT_DIR, include_drafts=False)
    assert not any(k.startswith(INSTRUMENT) for k in bundle.instruments)
    assert any(k.startswith(INSTRUMENT) for k in load_content(CONTENT_DIR).instruments)


def test_drafts_never_enabled_in_production():
    base = {
        "jwt_secret": "x" * 40,
        "email_provider": "smtp",
        "smtp_host": "h",
        "refresh_cookie_secure": True,
        "database_url": "postgresql+psycopg://u:p@h/db",
        "data_encryption_key": "k" * 44,
        "coach_provider": "anthropic",
        "anthropic_api_key": "k",
    }
    assert Settings(environment="production", **base).include_drafts is False
    with pytest.raises(ValidationError, match="Draft"):
        Settings(environment="production", content_include_drafts=True, **base)
    assert Settings(environment="development").include_drafts is True


def test_family_must_match_scoring(tmp_path):
    dst = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, dst)
    path = dst / "instruments" / f"{INSTRUMENT}.v1.0.0.json"
    data = json.loads(path.read_text())
    data["scoring"] = "likert_mean"
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match="count_endorsed"):
        load_content(dst)


def test_draft_may_change_but_released_may_not(tmp_path, db_url):
    content = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content)
    settings = Settings(environment="test", database_url=db_url, content_dir=content)
    with TestClient(create_app(settings, create_schema=True)):
        pass
    path = content / "instruments" / f"{INSTRUMENT}.v1.0.0.json"
    data = json.loads(path.read_text())
    data["items"][0]["text"] = "Build kitchen cabinets (corrected)"
    path.write_text(json.dumps(data, indent=2))
    with TestClient(create_app(settings)) as c:  # draft edits are accepted
        assert c.get(f"/api/v1/assessments/{INSTRUMENT}").json()["items"][0]["text"].endswith("(corrected)")
    data["status"] = "released"
    path.write_text(json.dumps(data, indent=2))
    with TestClient(create_app(settings)):  # first release registers the final hash
        pass
    data["items"][0]["text"] = "Something else"
    path.write_text(json.dumps(data, indent=2))
    with pytest.raises(ContentError, match="changed after release"), TestClient(create_app(settings)):
        pass


# ---------- API ----------


def _take(client, h, liked=("investigative", "artistic", "social"), headers=None):
    detail = client.get(f"/api/v1/assessments/{INSTRUMENT}").json()
    assert detail["family"] == "interests" and detail["status"] == "draft"
    assert [o["label"] for o in detail["response_options"]] == ["Not for me", "I'd like to do this"]
    inst = load_content(CONTENT_DIR).instrument(INSTRUMENT, "1.0.0").data
    area = {i.id: i.scale for i in inst.items}
    answers = [{"item_id": i["id"], "value": 2 if area[i["id"]] in liked else 1} for i in detail["items"]]
    r = client.put(
        f"/api/v1/assessment-sessions/{h['sid']}/answers", json={"answers": answers}, headers=headers
    )
    assert r.status_code == 200, r.text
    return client.post(f"/api/v1/assessment-sessions/{h['sid']}/complete", headers=headers)


def test_interest_assessment_end_to_end(client):
    sid, token_h, _ = start(client, INSTRUMENT)
    r = _take(client, {"sid": sid}, headers=token_h)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["kind"] == "interests" and res["archetypes"] is None and res["traits"] == []
    i = res["interests"]
    assert i["code"] == "IAS" and i["boundary_ties"] == [] and not i["empty"] and i["draft"]
    assert [(a["letter"], a["count"], a["score"]) for a in i["areas"][:3]] == [
        ("I", 10, 100.0),
        ("A", 10, 100.0),
        ("S", 10, 100.0),
    ]
    assert i["areas"][3]["count"] == 0
    assert all(a["fields"] and a["reflection"] for a in i["areas"])
    assert {lk["url"] for lk in i["explore_links"]} == {
        "https://www.mynextmove.org/",
        "https://www.onetonline.org/",
    }
    m = res["methodology"]
    assert "O*NET®" in m["attribution"] and "not affiliated" in m["attribution"]
    assert m["negative_emotionality_note"] is None
    assert any("not abilities" in lim for lim in m["limitations"])
    # Same result through the result endpoint.
    assert client.get(f"/api/v1/results/{res['id']}", headers=token_h).json() == res


def test_interest_results_in_history_and_coach_context(client):
    ada = signup(client)
    # A Big Five result and an interest result, both on the account.
    big5 = client.post(
        "/api/v1/assessment-sessions",
        headers=ada,
        json={"instrument_id": "mini-ipip-20", "consent": _consent()},
    ).json()
    _complete(client, big5["session"]["id"], ada)
    s = client.post(
        "/api/v1/assessment-sessions", headers=ada, json={"instrument_id": INSTRUMENT, "consent": _consent()}
    ).json()
    assert _take(client, {"sid": s["session"]["id"]}, liked=("enterprising",), headers=ada).status_code == 200

    hist = client.get("/api/v1/personality/history", headers=ada).json()["items"]
    assert any(h["primary_archetype"] == "Interest code ERI" for h in hist)

    conv = client.post(
        "/api/v1/coach/conversations", json={"consent": CONSENT, "topic": "career"}, headers=ada
    )
    p = use(client, Scripted(["Ok."]))
    send(client, ada, conv.json()["id"], "Which careers could I explore?")
    ctx = p.requests[0].system_context
    assert "code ERI" in ctx and "Enterprising 10 of 10" in ctx
    assert "Tied at third place" in ctx  # R, I, A, S and C are all 0
    assert "Openness:" in ctx  # the Big Five result is still used
    # Without shared results, neither is sent.
    conv2 = client.post(
        "/api/v1/coach/conversations", json={"consent": CONSENT, "use_results": False}, headers=ada
    )
    send(client, ada, conv2.json()["id"], "Hi")
    assert "Career interests" not in p.requests[1].system_context


def test_coach_context_with_only_interests(client, content):
    ada = signup(client)
    s = client.post(
        "/api/v1/assessment-sessions", headers=ada, json={"instrument_id": INSTRUMENT, "consent": _consent()}
    ).json()
    rid = _take(client, {"sid": s["session"]["id"]}, headers=ada).json()["id"]
    with db(client) as session:
        result = session.get(AssessmentResult, uuid.UUID(rid))
        facts = facts_from_result(content, None, "career", crisis_support_shown=False, interests=result)
    text = render_context(facts)
    assert "has not shared any assessment results" in text and "code IAS" in text


def _consent():
    from app.security.consent import CURRENT_POLICY_VERSION

    return {"accepted": True, "age_confirmed_18_plus": True, "policy_version": CURRENT_POLICY_VERSION}
