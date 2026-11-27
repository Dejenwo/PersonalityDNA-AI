import pytest

from app.leadership.profile import leadership_profile
from tests.test_auth import signup
from tests.test_careers import _consent
from tests.test_coach import CONSENT as COACH_CONSENT
from tests.test_coach import Scripted, send, use

INSTRUMENT = "leadership-preferences-27"
AREAS = [
    "strategic",
    "collaborative",
    "coaching",
    "delegating",
    "deciding",
    "communicating",
    "conflict",
    "team_development",
    "planning",
]


# ---------- profile (pure) ----------


def test_profile_ranking_ties_and_recommendations():
    scores = dict.fromkeys(AREAS, 50.0) | {"strategic": 100.0, "conflict": 25.0, "planning": 0.0}
    p = leadership_profile(scores, AREAS)
    assert p.ranking[0] == ("strategic", 100.0)
    assert p.top == ("strategic", "collaborative", "coaching")  # ties keep content order
    assert p.stretch == ("conflict", "planning")
    assert p.recommended == (("strategic", "build"), ("conflict", "stretch"), ("planning", "stretch"))
    assert not p.even


def test_profile_even_unscored_and_invalid():
    p = leadership_profile(dict.fromkeys(AREAS, 60.0) | {"planning": 55.0}, AREAS)
    assert p.even
    partial = leadership_profile({"strategic": 10.0, "planning": None}, AREAS)
    assert partial.ranking == (("strategic", 10.0),) and partial.stretch == ()
    assert leadership_profile({}, AREAS).recommended == ()
    with pytest.raises(ValueError):
        leadership_profile({"charisma": 1.0}, AREAS)


# ---------- content ----------


def test_instrument_and_program(content):
    inst = content.instrument(INSTRUMENT, "1.0.0").data
    assert (inst.family, inst.scoring, inst.status) == ("leadership", "likert_mean", "released")
    assert [s.id for s in inst.scales] == AREAS
    assert len(inst.items) == 27 and all(i.keyed == "+" for i in inst.items)
    # Areas are interleaved so similar statements are not answered back to back.
    assert [i.scale for i in inst.items[:9]] == AREAS
    assert inst.license.file == "licenses/ORIGINAL_CONTENT.md"
    program = content.leadership.data
    assert list(program.areas) == AREAS
    assert all(program.module(a.module) for a in program.areas.values())
    assert all(len(m.activities) >= 2 and m.lessons for m in program.modules)


# ---------- API ----------


def _take(client, headers=None, high=("strategic",), low=(("conflict", 2), ("planning", 1))):
    s = client.post(
        "/api/v1/assessment-sessions",
        headers=headers,
        json={"instrument_id": INSTRUMENT, "consent": _consent()},
    ).json()
    h = headers or {"X-Session-Token": s["resume_token"]}
    detail = client.get(f"/api/v1/assessments/{INSTRUMENT}").json()
    area = {i.id: i.scale for i in _inst(client).items}
    lows = dict(low)
    answers = [
        {"item_id": i["id"], "value": 5 if area[i["id"]] in high else lows.get(area[i["id"]], 3)}
        for i in detail["items"]
    ]
    client.put(
        f"/api/v1/assessment-sessions/{s['session']['id']}/answers", json={"answers": answers}, headers=h
    )
    r = client.post(f"/api/v1/assessment-sessions/{s['session']['id']}/complete", headers=h)
    assert r.status_code == 200, r.text
    return r.json(), h


def _inst(client):
    return client.app.state.content.instrument(INSTRUMENT, "1.0.0").data


def test_leadership_result(client):
    res, h = _take(client)
    assert res["kind"] == "leadership" and res["archetypes"] is None and res["interests"] is None
    lead = res["leadership"]
    assert [(a["area"], a["score"]) for a in lead["areas"]][:2] == [
        ("strategic", 100.0),
        ("collaborative", 50.0),
    ]
    assert [a["area"] for a in lead["areas"]][-2:] == ["conflict", "planning"]
    assert lead["top"] == ["strategic", "collaborative", "coaching"]
    assert lead["stretch"] == ["conflict", "planning"]
    assert [(m["id"], m["reason"]) for m in lead["recommended_modules"]] == [
        ("direction", "build"),
        ("constructive-conflict", "stretch"),
        ("plans-that-work", "stretch"),
    ]
    by = {a["area"]: a for a in lead["areas"]}
    assert by["planning"]["text"].startswith("Writing down milestones")  # stretch text for low areas
    assert by["strategic"]["text"].startswith("You may naturally")
    m = res["methodology"]
    assert any("not been scientifically validated" in x for x in m["limitations"])
    assert any("never be used to hire" in x for x in m["limitations"])
    assert client.get(f"/api/v1/results/{res['id']}", headers=h).json() == res


def test_modules_and_progress(client):
    listing = client.get("/api/v1/leadership/modules").json()
    assert len(listing["modules"]) == 9 and all(m["activities_done"] == 0 for m in listing["modules"])
    assert client.get("/api/v1/leadership/modules/nope").status_code == 404
    module = client.get("/api/v1/leadership/modules/delegation").json()
    assert module["area"] == "delegating" and module["lessons"] and module["reflection"]
    assert all(a["completed_at"] is None for a in module["activities"])

    url = "/api/v1/leadership/modules/delegation/activities/handover/done"
    assert client.put(url).status_code == 401
    ada = signup(client)
    assert client.put(url, headers=ada).status_code == 204
    first = client.get("/api/v1/leadership/modules/delegation", headers=ada).json()["activities"][0][
        "completed_at"
    ]
    assert client.put(url, headers=ada).status_code == 204  # idempotent, keeps the first time
    again = client.get("/api/v1/leadership/modules/delegation", headers=ada).json()["activities"][0]
    assert again["completed_at"] == first
    done = {
        m["id"]: m["activities_done"]
        for m in client.get("/api/v1/leadership/modules", headers=ada).json()["modules"]
    }
    assert done["delegation"] == 1 and sum(done.values()) == 1
    # Other users and anonymous visitors see their own progress only.
    bob = signup(client, "bob@example.com")
    assert (
        client.get("/api/v1/leadership/modules/delegation", headers=bob).json()["activities"][0][
            "completed_at"
        ]
        is None
    )

    assert (
        client.put("/api/v1/leadership/modules/delegation/activities/nope/done", headers=ada).status_code
        == 404
    )
    export = client.get("/api/v1/privacy/export", headers=ada).json()
    assert export["leadership_activities"][0]["activity"] == "handover"
    assert client.delete(url, headers=ada).status_code == 204
    assert client.get("/api/v1/leadership/modules", headers=ada).json()["modules"][3]["activities_done"] == 0


def test_history_and_coach_context(client):
    ada = signup(client)
    _take(client, headers=ada)
    hist = client.get("/api/v1/personality/history", headers=ada).json()["items"]
    assert hist[0]["primary_archetype"] == "Top preference: Strategic thinking"

    conv = client.post(
        "/api/v1/coach/conversations", json={"consent": COACH_CONSENT, "topic": "leadership"}, headers=ada
    )
    assert conv.status_code == 201, conv.text
    p = use(client, Scripted(["Ok."]))
    send(client, ada, conv.json()["id"], "How could I grow as a leader?")
    ctx = p.requests[0].system_context
    assert "most preferred Strategic thinking, Collaborating, Coaching others" in ctx
    assert "least preferred Handling conflict, Planning and organising" in ctx
    assert "has not shared any assessment results" in ctx  # no Big Five result on this account
