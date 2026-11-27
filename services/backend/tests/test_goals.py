"""Goals, milestones and habits: encryption, ownership, history and gentle analytics."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.database.models import Goal, Habit, HabitCheck
from app.goals import stats
from tests.test_auth import PASSWORD, db, signup

TODAY = datetime.now(UTC).date()


# ---------- stats (pure) ----------


def test_masks():
    assert stats.days_to_mask([0, 2, 4]) == 0b10101
    assert stats.mask_to_days(0b1100000) == [5, 6]
    assert stats.days_to_mask(list(range(7))) == stats.EVERY_DAY
    for bad in ([], [7], [-1]):
        with pytest.raises(ValueError):
            stats.days_to_mask(bad)
    assert stats.is_planned(0b1, date(2026, 11, 23))  # a Monday
    assert not stats.is_planned(0b1, date(2026, 11, 24))


def test_window_counts_planned_and_extra_days():
    # Mondays, Wednesdays and Fridays; today is Sunday 29 November 2026.
    mask, today = stats.days_to_mask([0, 2, 4]), date(2026, 11, 29)
    done = {date(2026, 11, 23), date(2026, 11, 27), date(2026, 11, 28)}  # Mon, Fri, Sat
    w = stats.window(mask, done, date(2026, 1, 1), today, 7)
    assert (w.planned, w.done_on_planned, w.done_extra) == (3, 2, 1)
    # A habit started on Thursday only counts from then: Friday is the only planned day.
    w = stats.window(mask, done, date(2026, 11, 26), today, 30)
    assert (w.planned, w.done_on_planned, w.done_extra) == (1, 1, 1)


def test_grid_is_whole_weeks_ending_this_week():
    g = stats.grid(stats.EVERY_DAY, {date(2026, 11, 25)}, date(2026, 11, 25), weeks=2)
    assert len(g) == 14 and g[0].day == date(2026, 11, 16) and g[-1].day == date(2026, 11, 29)
    assert [d.day for d in g if d.done] == [date(2026, 11, 25)]


# ---------- goals ----------


def test_goal_lifecycle_and_privacy(client):
    assert client.get("/api/v1/goals").status_code == 401
    ada = signup(client)
    r = client.post(
        "/api/v1/goals",
        json={
            "title": "Run a 5k",
            "why": "To feel stronger",
            "target_date": "2027-03-01",
            "milestones": [{"title": "Run 1k"}, {"title": "Run 3k", "due_date": "2027-01-15"}],
        },
        headers=ada,
    )
    assert r.status_code == 201, r.text
    g = r.json()
    assert (g["title"], g["why"], g["status"], g["milestones_done"]) == (
        "Run a 5k",
        "To feel stronger",
        "active",
        0,
    )
    assert [m["title"] for m in g["milestones"]] == ["Run 1k", "Run 3k"]
    with db(client) as s:
        row = s.scalars(select(Goal)).one()
    # Whole phrases: they contain spaces, which base64 ciphertext never does, so this can't match by chance.
    assert "Run a 5k" not in row.title_encrypted and "To feel stronger" not in (row.why_encrypted or "")

    gid, m1 = g["id"], g["milestones"][0]["id"]
    g = client.patch(f"/api/v1/goals/{gid}/milestones/{m1}", json={"done": True}, headers=ada).json()
    assert g["milestones_done"] == 1 and g["milestones"][0]["done_at"]
    g = client.post(f"/api/v1/goals/{gid}/milestones", json={"title": "Run 5k"}, headers=ada).json()
    assert [m["title"] for m in g["milestones"]] == ["Run 1k", "Run 3k", "Run 5k"]
    g = client.delete(f"/api/v1/goals/{gid}/milestones/{g['milestones'][1]['id']}", headers=ada).json()
    assert [m["title"] for m in g["milestones"]] == ["Run 1k", "Run 5k"]

    # Adjusting the goal: only sent fields change; null clears.
    g = client.patch(
        f"/api/v1/goals/{gid}", json={"target_date": None, "title": "Run a 10k"}, headers=ada
    ).json()
    assert (g["title"], g["target_date"], g["why"]) == ("Run a 10k", None, "To feel stronger")
    g = client.patch(f"/api/v1/goals/{gid}", json={"status": "completed"}, headers=ada).json()
    assert g["status"] == "completed" and g["completed_at"]
    g = client.patch(f"/api/v1/goals/{gid}", json={"status": "active"}, headers=ada).json()
    assert g["completed_at"] is None
    assert client.patch(f"/api/v1/goals/{gid}", json={"status": "won"}, headers=ada).status_code == 422

    bob = signup(client, "bob@example.com")
    for method, url in (
        ("GET", f"/api/v1/goals/{gid}"),
        ("DELETE", f"/api/v1/goals/{gid}"),
        ("PATCH", f"/api/v1/goals/{gid}/milestones/{m1}"),
    ):
        assert client.request(method, url, json={}, headers=bob).status_code == 404
    assert client.get("/api/v1/goals", headers=bob).json()["goals"] == []
    assert client.get("/api/v1/goals/nope", headers=ada).status_code == 404


def test_goal_validation(client):
    ada = signup(client)
    assert client.post("/api/v1/goals", json={"title": ""}, headers=ada).status_code == 422
    many = [{"title": str(i)} for i in range(21)]
    assert (
        client.post("/api/v1/goals", json={"title": "x", "milestones": many}, headers=ada).status_code == 422
    )


# ---------- habits ----------


def _habit(client, h, **kw):
    r = client.post("/api/v1/habits", json={"title": "Read 10 pages", **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_habit_checks_history_and_stats(client):
    ada = signup(client)
    h = _habit(client, ada)
    assert h["weekdays"] == list(range(7)) and h["start_date"] == TODAY.isoformat()
    assert not h["done_today"] and h["planned_today"]
    url = f"/api/v1/habits/{h['id']}/checks"
    h = client.put(f"{url}/{TODAY}", headers=ada).json()
    assert h["done_today"] and h["last_7"]["done_on_planned"] == 1 and h["last_7"]["planned"] == 1
    assert client.put(f"{url}/{TODAY}", headers=ada).json()["last_7"]["done_on_planned"] == 1  # idempotent
    # Back-filling before the start date moves the start, so the history counts it.
    three_ago = TODAY - timedelta(days=3)
    h = client.put(f"{url}/{three_ago}", headers=ada).json()
    assert h["start_date"] == three_ago.isoformat() and h["last_7"]["planned"] == 4
    assert h["last_7"]["done_on_planned"] == 2
    assert sum(d["done"] for d in h["grid"]) == 2 and len(h["grid"]) == 28
    # Limits on dates.
    assert client.put(f"{url}/{TODAY + timedelta(days=1)}", headers=ada).status_code == 422
    assert client.put(f"{url}/{TODAY - timedelta(days=31)}", headers=ada).status_code == 422
    h = client.delete(f"{url}/{TODAY}", headers=ada).json()
    assert not h["done_today"]
    # The user's local date is accepted within a day of the server's.
    assert client.get(f"/api/v1/habits?today={TODAY + timedelta(days=1)}", headers=ada).status_code == 200
    assert client.get(f"/api/v1/habits?today={TODAY + timedelta(days=3)}", headers=ada).status_code == 422

    with db(client) as s:
        assert "Read" not in s.scalars(select(Habit)).one().title_encrypted


def test_habits_link_to_goals_archive_and_delete(client):
    ada = signup(client)
    goal = client.post("/api/v1/goals", json={"title": "Learn Spanish"}, headers=ada).json()
    h = _habit(client, ada, title="Practise vocabulary", weekdays=[0, 2, 4], goal_id=goal["id"])
    assert h["goal_id"] == goal["id"] and h["weekdays"] == [0, 2, 4]
    assert client.get(f"/api/v1/goals/{goal['id']}", headers=ada).json()["habits"] == [h["id"]]
    assert client.post("/api/v1/habits", json={"title": "x", "weekdays": [9]}, headers=ada).status_code == 422
    assert client.post("/api/v1/habits", json={"title": "x", "weekdays": []}, headers=ada).status_code == 422

    bob = signup(client, "bob@example.com")
    # Bob can't link to Ada's goal or touch Ada's habit.
    assert (
        client.post("/api/v1/habits", json={"title": "x", "goal_id": goal["id"]}, headers=bob).status_code
        == 404
    )
    assert client.put(f"/api/v1/habits/{h['id']}/checks/{TODAY}", headers=bob).status_code == 404

    h = client.patch(
        f"/api/v1/habits/{h['id']}", json={"archived": True, "weekdays": [5, 6]}, headers=ada
    ).json()
    assert h["archived"] and h["weekdays"] == [5, 6]
    other = _habit(client, ada, title="Walk")
    assert [x["id"] for x in client.get("/api/v1/habits", headers=ada).json()["habits"]] == [
        other["id"],
        h["id"],
    ]

    # Deleting the goal keeps the habit and unlinks it.
    assert client.delete(f"/api/v1/goals/{goal['id']}", headers=ada).status_code == 204
    habits = {x["id"]: x for x in client.get("/api/v1/habits", headers=ada).json()["habits"]}
    assert habits[h["id"]]["goal_id"] is None

    client.put(f"/api/v1/habits/{other['id']}/checks/{TODAY}", headers=ada)
    export = client.get("/api/v1/privacy/export", headers=ada).json()["goals_and_habits"]
    assert {x["title"] for x in export["habits"]} == {"Practise vocabulary", "Walk"}
    walk = next(x for x in export["habits"] if x["title"] == "Walk")
    assert walk["days_done"] == [TODAY.isoformat()]

    assert client.delete(f"/api/v1/habits/{other['id']}", headers=ada).status_code == 204
    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204
    with db(client) as s:
        assert s.scalars(select(Habit)).all() == [] and s.scalars(select(HabitCheck)).all() == []
        assert s.scalars(select(Goal)).all() == []
