"""Personal growth academy: programme content, the day plan, enrolment, progress and self-evaluation."""

from sqlalchemy import func, select

from app.database.models import GrowthCheckIn, GrowthDayProgress, GrowthEnrollment
from app.growth.plan import next_day, plan_days
from tests.test_auth import PASSWORD, db, signup

G = "/api/v1/growth/programs"


# ---------- content and plan (pure) ----------


def test_programme_lengths_and_content(content):
    academy = content.growth.data
    lengths = sorted({p.days for p in academy.programs})
    assert lengths == [7, 30, 60, 90]
    for p in academy.programs:
        days = plan_days(academy, p)
        assert [d.day for d in days] == list(range(1, p.days + 1))
        assert all(d.text for d in days) and p.objectives
    # The 90-day programme covers every week once.
    ninety = academy.program("personal-growth-90")
    assert ninety is not None and sorted(ninety.weeks) == sorted(w.id for w in academy.weeks)
    topics = {w.topic for w in academy.weeks}
    assert {
        "communication",
        "leadership",
        "organization",
        "confidence",
        "productivity",
        "decision-making",
        "relationship-communication",
        "goal-setting",
        "career-exploration",
        "self-awareness",
    } <= topics
    assert "not therapy" in academy.note and "not scores" in academy.note


def test_plan_week_structure(content):
    academy = content.growth.data
    p = academy.program("foundations-30")
    assert p is not None
    days = plan_days(academy, p)
    first = academy.week(p.weeks[0])
    assert [d.kind for d in days[:7]] == ["lesson"] + ["exercise"] * 5 + ["milestone"]
    assert (
        days[0].text == first.lesson.text
        and days[1].text == first.daily[0]
        and days[6].text == first.milestone
    )
    assert days[7].week == 2 and days[7].kind == "lesson"
    assert [(d.day, d.kind, d.week) for d in days[28:]] == [(29, "review", None), (30, "review", None)]
    assert days[28].text == academy.review_days[0]


def test_next_day():
    assert next_day(7, set()) == 1
    assert next_day(7, {1, 2, 4}) == 3
    assert next_day(3, {1, 2, 3}) is None


# ---------- API ----------


def test_listing_and_detail_without_account(client):
    listing = client.get(G).json()
    assert [p["id"] for p in listing["programs"]][:3] == ["confidence-7", "focus-7", "clear-communication-7"]
    by = {p["id"]: p for p in listing["programs"]}
    assert by["confidence-7"]["kind"] == "challenge" and by["foundations-30"]["kind"] == "program"
    assert all(p["enrollment"] is None for p in listing["programs"])
    assert by["communication-30"]["topics"] == ["communication", "relationship-communication", "confidence"]
    detail = client.get(f"{G}/work-and-career-60").json()
    assert detail["days"] == 60 and len(detail["weeks"]) == 8 and len(detail["review_days"]) == 4
    assert detail["self_evaluation_scale"][0] == "Not at all"
    w1 = detail["weeks"][0]
    assert [d["day"] for d in w1["days"]] == list(range(1, 8)) and w1["rating"] is None
    assert client.get(f"{G}/nope").status_code == 404


def test_enrol_progress_check_in_and_restart(client):
    url = f"{G}/confidence-7"
    assert client.post(f"{url}/enrollment").status_code == 401
    ada = signup(client)
    # Progress needs an enrolment first.
    r = client.put(f"{url}/days/1/done", headers=ada)
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_enrolled"

    started = client.post(f"{url}/enrollment", headers=ada)
    assert started.status_code == 200, started.text
    assert started.json()["enrollment"]["days_done"] == 0 and started.json()["enrollment"]["next_day"] == 1

    for day in (1, 2, 4):
        assert client.put(f"{url}/days/{day}/done", headers=ada).status_code == 204
    assert client.put(f"{url}/days/1/done", headers=ada).status_code == 204  # idempotent
    assert client.put(f"{url}/days/8/done", headers=ada).status_code == 404
    assert client.put(f"{url}/days/0/done", headers=ada).status_code == 404
    e = client.get(url, headers=ada).json()["enrollment"]
    assert e["days_done"] == 3 and e["next_day"] == 3 and e["completed_at"] is None

    assert client.put(f"{url}/weeks/1/check-in", json={"rating": 4}, headers=ada).status_code == 204
    assert client.put(f"{url}/weeks/1/check-in", json={"rating": 5}, headers=ada).status_code == 204
    assert client.put(f"{url}/weeks/1/check-in", json={"rating": 6}, headers=ada).status_code == 422
    assert client.put(f"{url}/weeks/2/check-in", json={"rating": 3}, headers=ada).status_code == 404
    assert client.get(url, headers=ada).json()["weeks"][0]["rating"] == 5

    for day in range(1, 8):
        client.put(f"{url}/days/{day}/done", headers=ada)
    e = client.get(url, headers=ada).json()["enrollment"]
    assert e["completed_at"] is not None and e["next_day"] is None
    assert client.delete(f"{url}/days/7/done", headers=ada).status_code == 204
    e = client.get(url, headers=ada).json()["enrollment"]
    assert e["completed_at"] is None and e["next_day"] == 7

    # Other users see their own progress only.
    bob = signup(client, "bob@example.com")
    assert client.get(url, headers=bob).json()["enrollment"] is None
    assert client.put(f"{url}/days/1/done", headers=bob).status_code == 409

    export = client.get("/api/v1/privacy/export", headers=ada).json()["growth_programs"]
    assert export[0]["program"] == "confidence-7" and len(export[0]["days_done"]) == 6
    assert export[0]["self_evaluations"] == [{"week": 1, "rating": 5}]

    # Restarting clears progress and self-evaluations.
    restarted = client.post(f"{url}/enrollment", headers=ada).json()
    assert restarted["enrollment"]["days_done"] == 0 and restarted["weeks"][0]["rating"] is None
    listing = {p["id"]: p for p in client.get(G, headers=ada).json()["programs"]}
    assert listing["confidence-7"]["enrollment"]["next_day"] == 1 and listing["focus-7"]["enrollment"] is None

    assert client.delete(f"{url}/weeks/1/check-in", headers=ada).status_code == 204
    assert client.delete(f"{url}/enrollment", headers=ada).status_code == 204
    assert client.get(url, headers=ada).json()["enrollment"] is None
    assert client.get("/api/v1/privacy/export", headers=ada).json()["growth_programs"] == []


def test_account_deletion_removes_growth_progress(client):
    ada = signup(client)
    client.post(f"{G}/focus-7/enrollment", headers=ada)
    client.put(f"{G}/focus-7/days/1/done", headers=ada)
    client.put(f"{G}/focus-7/weeks/1/check-in", json={"rating": 2}, headers=ada)
    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204, r.text
    with db(client) as s:
        for model in (GrowthEnrollment, GrowthDayProgress, GrowthCheckIn):
            assert s.scalar(select(func.count()).select_from(model)) == 0
