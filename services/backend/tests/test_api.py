from app.security.consent import CURRENT_POLICY_VERSION
from tests.conftest import CONSENT, start


def test_health_and_security_headers(client):
    r = client.get("/health")
    assert r.json() == {"status": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/v1/assessments").headers["cache-control"] == "no-store"


def test_list_and_detail(client):
    items = client.get("/api/v1/assessments").json()["items"]
    assert [(i["id"], i["item_count"], i["tier"]) for i in items] == [
        ("mini-ipip-20", 20, "quick"),
        ("ipip-bfm-50", 50, "comprehensive"),
        ("onet-ipsf-60", 60, "quick"),
        ("leadership-preferences-27", 27, "quick"),
    ]
    d = client.get("/api/v1/assessments/ipip-bfm-50").json()
    assert len(d["items"]) == 50 and len(d["response_options"]) == 5
    # Scoring keys are server-side only.
    assert "keyed" not in d["items"][0] and "scale" not in d["items"][0]
    assert client.get("/api/v1/assessments/nope").status_code == 404


def test_full_flow_save_resume_complete(client):
    sid, h, body = start(client)
    assert body["session"]["progress"] == {"answered": 0, "total": 20, "percent": 0.0}
    items = client.get("/api/v1/assessments/mini-ipip-20").json()["items"]

    first = [{"item_id": i["id"], "value": 4} for i in items[:10]]
    r = client.put(f"/api/v1/assessment-sessions/{sid}/answers", json={"answers": first}, headers=h)
    assert r.status_code == 200 and r.json()["progress"]["answered"] == 10

    # Resume: answers come back.
    s = client.get(f"/api/v1/assessment-sessions/{sid}", headers=h).json()
    assert s["status"] == "in_progress" and len(s["answers"]) == 10

    # Completing early is refused with the missing items listed.
    r = client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "incomplete"
    assert len(r.json()["error"]["details"]["missing_items"]) == 10

    rest = [{"item_id": i["id"], "value": (n % 5) + 1} for n, i in enumerate(items[10:])]
    client.put(f"/api/v1/assessment-sessions/{sid}/answers", json={"answers": rest}, headers=h)
    r = client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h)
    assert r.status_code == 200, r.text
    result = r.json()
    assert len(result["traits"]) == 5
    assert all(0 <= t["score"] <= 100 for t in result["traits"])
    stab = next(t["score"] for t in result["traits"] if t["trait"] == "emotional_stability")
    assert result["negative_emotionality"] == round(100 - stab, 1)
    assert result["archetypes"]["primary"]["id"] != result["archetypes"]["secondary"]["id"]
    assert result["methodology"]["engine_version"] == "1.1.0"
    assert "rapid_completion" in result["quality_flags"]  # test runs in well under 30s

    # Idempotent completion returns the same result.
    again = client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h).json()
    assert again["id"] == result["id"]
    fetched = client.get(f"/api/v1/results/{result['id']}", headers=h).json()
    assert fetched == result

    # Session is closed for edits.
    r = client.put(f"/api/v1/assessment-sessions/{sid}/answers", json={"answers": first}, headers=h)
    assert r.status_code == 409


def test_same_answers_same_scores_across_sessions(client):
    items = client.get("/api/v1/assessments/mini-ipip-20").json()["items"]
    answers = [{"item_id": i["id"], "value": ((n * 7) % 5) + 1} for n, i in enumerate(items)]
    results = []
    for _ in range(3):
        sid, h, _ = start(client)
        client.put(f"/api/v1/assessment-sessions/{sid}/answers", json={"answers": answers}, headers=h)
        results.append(client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h).json())
    assert len({tuple((t["trait"], t["score"]) for t in r["traits"]) for r in results}) == 1
    assert len({r["methodology"]["answers_sha256"] for r in results}) == 1


def test_clearing_an_answer(client):
    sid, h, _ = start(client)
    client.put(
        f"/api/v1/assessment-sessions/{sid}/answers",
        json={"answers": [{"item_id": "mini20-01", "value": 3}]},
        headers=h,
    )
    r = client.put(
        f"/api/v1/assessment-sessions/{sid}/answers",
        json={"answers": [{"item_id": "mini20-01", "value": None}]},
        headers=h,
    )
    assert r.json()["progress"]["answered"] == 0


def test_object_level_authorization(client):
    sid_a, h_a, _ = start(client)
    _, h_b, _ = start(client)
    assert client.get(f"/api/v1/assessment-sessions/{sid_a}").status_code == 404
    assert client.get(f"/api/v1/assessment-sessions/{sid_a}", headers=h_b).status_code == 404
    r = client.put(
        f"/api/v1/assessment-sessions/{sid_a}/answers",
        json={"answers": [{"item_id": "mini20-01", "value": 3}]},
        headers=h_b,
    )
    assert r.status_code == 404
    assert client.get(f"/api/v1/assessment-sessions/{sid_a}", headers=h_a).status_code == 200
    assert client.get("/api/v1/assessment-sessions/not-a-uuid", headers=h_a).status_code == 422


def test_result_requires_owning_token(client):
    items = client.get("/api/v1/assessments/mini-ipip-20").json()["items"]
    sid, h, _ = start(client)
    client.put(
        f"/api/v1/assessment-sessions/{sid}/answers",
        json={"answers": [{"item_id": i["id"], "value": 2} for i in items]},
        headers=h,
    )
    rid = client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h).json()["id"]
    _, other, _ = start(client)
    assert client.get(f"/api/v1/results/{rid}", headers=other).status_code == 404
    assert client.get(f"/api/v1/results/{rid}").status_code == 404


def test_consent_and_age_required(client):
    url = "/api/v1/assessment-sessions"
    r = client.post(url, json={"instrument_id": "mini-ipip-20", "consent": {**CONSENT, "accepted": False}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "consent_required"
    r = client.post(
        url, json={"instrument_id": "mini-ipip-20", "consent": {**CONSENT, "age_confirmed_18_plus": False}}
    )
    assert r.json()["error"]["code"] == "age_requirement"
    r = client.post(
        url, json={"instrument_id": "mini-ipip-20", "consent": {**CONSENT, "policy_version": "old"}}
    )
    assert r.status_code == 409
    assert r.json()["error"]["details"]["current_policy_version"] == CURRENT_POLICY_VERSION


def test_invalid_answers_rejected(client):
    sid, h, _ = start(client)
    url = f"/api/v1/assessment-sessions/{sid}/answers"
    assert client.put(url, json={"answers": [{"item_id": "x", "value": 3}]}, headers=h).status_code == 422
    assert (
        client.put(url, json={"answers": [{"item_id": "mini20-01", "value": 9}]}, headers=h).status_code
        == 422
    )
    assert client.put(url, json={"answers": []}, headers=h).status_code == 422
    r = client.put(url, json={"answers": [{"item_id": "mini20-01", "value": 3, "extra": 1}]}, headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_unknown_instrument_and_locale(client):
    url = "/api/v1/assessment-sessions"
    assert client.post(url, json={"instrument_id": "nope", "consent": CONSENT}).status_code == 404
    r = client.post(url, json={"instrument_id": "mini-ipip-20", "locale": "am", "consent": CONSENT})
    assert r.json()["error"]["code"] == "locale_unavailable"


def test_session_creation_rate_limited(settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings.session_create_rate_limit = 2
    with TestClient(create_app(settings, create_schema=True)) as c:
        codes = [
            c.post(
                "/api/v1/assessment-sessions", json={"instrument_id": "mini-ipip-20", "consent": CONSENT}
            ).status_code
            for _ in range(3)
        ]
    assert codes == [201, 201, 429]


def test_token_stored_only_as_hash(client):
    from sqlalchemy import select

    from app.database.models import AssessmentSession

    _, h, _ = start(client)
    with client.app.state.db.sessionmaker() as s:
        row = s.scalar(select(AssessmentSession))
    assert row.token_hash != h["X-Session-Token"] and len(row.token_hash) == 64


def test_docs_hidden_in_production(settings):
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings.environment = "production"
    with TestClient(create_app(settings, create_schema=True)) as c:
        assert c.get("/openapi.json").status_code == 404
