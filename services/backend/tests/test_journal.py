"""Private journal: encryption at rest, ownership, search, tags, export and deletion."""

import pytest
from sqlalchemy import select

from app.api.errors import ApiError
from app.database.models import JournalEntry
from app.journal.service import decode_cursor, encode_cursor, normalize_tags
from tests.test_auth import PASSWORD, db, signup

J = "/api/v1/journal"


def _new(client, h, body="Walked to work and felt calm.", **kw):
    r = client.post(f"{J}/entries", json={"body": body, **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_tag_normalisation_and_cursor():
    assert normalize_tags(["  Work ", "#work", "Deep   Focus", "", "family"]) == [
        "work",
        "deep focus",
        "family",
    ]
    with pytest.raises(ApiError):
        normalize_tags(["x" * 33])
    assert decode_cursor(encode_cursor(40)) == 40 and decode_cursor(None) == 0
    for bad in ("nope", encode_cursor(-1)):
        with pytest.raises(ApiError):
            decode_cursor(bad)


def test_prompts_are_public_and_cover_every_kind(client):
    p = client.get(f"{J}/prompts").json()
    assert [k["id"] for k in p["kinds"]] == [
        "daily",
        "gratitude",
        "goal",
        "development",
        "communication",
        "free",
    ]
    assert all(k["prompts"] for k in p["kinds"]) and len(p["mood_scale"]) == 5
    assert "never sent to the AI coach" in p["note"] and "988" in p["support_note"]


def test_entries_are_encrypted_and_private(client):
    assert client.get(f"{J}/entries").status_code == 401
    ada = signup(client)
    e = _new(
        client, ada, body="A secret about my day", title="Tuesday", mood=4, tags=["Work", "#work", "calm"]
    )
    assert (e["title"], e["mood"], e["tags"], e["kind"]) == ("Tuesday", 4, ["work", "calm"], "daily")
    with db(client) as s:
        row = s.scalars(select(JournalEntry)).one()
        stored = " ".join([row.title_encrypted or "", row.body_encrypted, row.tags_encrypted])
    assert "secret" not in stored and "Tuesday" not in stored and "work" not in stored
    assert row.body_encrypted.startswith("v1:")

    bob = signup(client, "bob@example.com")
    assert client.get(f"{J}/entries/{e['id']}", headers=bob).status_code == 404
    assert client.patch(f"{J}/entries/{e['id']}", json={"body": "x"}, headers=bob).status_code == 404
    assert client.delete(f"{J}/entries/{e['id']}", headers=bob).status_code == 404
    assert client.get(f"{J}/entries", headers=bob).json()["items"] == []
    assert client.get(f"{J}/entries/not-a-uuid", headers=ada).status_code == 404


def test_create_validation(client):
    ada = signup(client)
    for bad in (
        {"body": ""},
        {"body": "x", "mood": 6},
        {"body": "x", "kind": "dream"},
        {"body": "x", "tags": [str(i) for i in range(11)]},
        {"body": "x" * 20_001},
    ):
        assert client.post(f"{J}/entries", json=bad, headers=ada).status_code == 422, bad
    r = client.post(f"{J}/entries", json={"body": "x", "entry_date": "2999-01-01"}, headers=ada)
    assert r.status_code == 422 and r.json()["error"]["code"] == "future_date"


def test_update_list_and_pagination(client):
    ada = signup(client)
    e = _new(client, ada, title="Old", mood=2, tags=["a"])
    updated = client.patch(f"{J}/entries/{e['id']}", json={"title": None, "tags": ["b"]}, headers=ada).json()
    assert updated["title"] is None and updated["tags"] == ["b"] and updated["mood"] == 2
    assert updated["body"] == e["body"]
    updated = client.patch(
        f"{J}/entries/{e['id']}", json={"mood": None, "kind": "gratitude"}, headers=ada
    ).json()
    assert updated["mood"] is None and updated["kind"] == "gratitude"

    for i, day in enumerate(["2026-01-02", "2026-01-03", "2026-01-01"]):
        _new(client, ada, body=f"entry {i}", entry_date=day)
    page1 = client.get(f"{J}/entries?limit=2", headers=ada).json()
    assert len(page1["items"]) == 2 and page1["next_cursor"]
    page2 = client.get(f"{J}/entries?limit=2&cursor={page1['next_cursor']}", headers=ada).json()
    assert page2["next_cursor"] is None
    dates = [x["entry_date"] for x in page1["items"] + page2["items"]]
    assert dates == sorted(dates, reverse=True) and len(dates) == 4


def test_search_and_tags(client):
    ada = signup(client)
    _new(
        client,
        ada,
        body="Long walk with Sam in the park",
        tags=["friends", "outdoors"],
        entry_date="2026-03-01",
    )
    _new(
        client,
        ada,
        body="Difficult meeting at work",
        kind="communication",
        tags=["work"],
        entry_date="2026-03-02",
    )
    _new(
        client,
        ada,
        body="Grateful for the park nearby",
        kind="gratitude",
        tags=["outdoors"],
        entry_date="2026-03-03",
    )

    def search(**kw):
        r = client.post(f"{J}/search", json=kw, headers=ada)
        assert r.status_code == 200, r.text
        return [x["body"] for x in r.json()["items"]]

    assert search(q="PARK") == ["Grateful for the park nearby", "Long walk with Sam in the park"]
    assert search(q="walk park") == ["Long walk with Sam in the park"]
    assert search(q="friends") == ["Long walk with Sam in the park"]  # tags are searched too
    assert search(tag="#Outdoors", kind="gratitude") == ["Grateful for the park nearby"]
    assert search(date_from="2026-03-02", date_to="2026-03-02") == ["Difficult meeting at work"]
    assert search(q="nothing like this") == []
    paged = client.post(f"{J}/search", json={"q": "park", "limit": 1}, headers=ada).json()
    assert len(paged["items"]) == 1 and paged["next_cursor"]
    tags = client.get(f"{J}/tags", headers=ada).json()["tags"]
    assert tags == [
        {"tag": "outdoors", "count": 2},
        {"tag": "friends", "count": 1},
        {"tag": "work", "count": 1},
    ]
    assert (
        client.post(f"{J}/search", json={"q": "park"}, headers=signup(client, "bob@example.com")).json()[
            "items"
        ]
        == []
    )


def test_export_and_deletion(client):
    ada = signup(client)
    _new(client, ada, body="First entry", title="Hello", mood=5, tags=["start"], entry_date="2026-02-01")
    _new(client, ada, body="Second entry", kind="gratitude", entry_date="2026-02-02")
    md = client.get(f"{J}/export", headers=ada)
    assert md.status_code == 200 and md.headers["content-type"].startswith("text/markdown")
    assert 'filename="journal.md"' in md.headers["content-disposition"]
    assert md.headers["cache-control"] == "no-store"
    assert (
        "## 2026-02-01: Hello" in md.text and "*Daily reflection · mood: Very good · tags: start*" in md.text
    )
    assert "## 2026-02-02: Gratitude" in md.text
    js = client.get(f"{J}/export?format=json", headers=ada).json()
    assert [e["body"] for e in js] == ["Second entry", "First entry"]
    assert client.get(f"{J}/export?format=pdf", headers=ada).status_code == 422
    privacy = client.get("/api/v1/privacy/export", headers=ada).json()
    assert [e["body"] for e in privacy["journal_entries"]] == ["Second entry", "First entry"]

    one = client.get(f"{J}/entries", headers=ada).json()["items"][0]["id"]
    assert client.delete(f"{J}/entries/{one}", headers=ada).status_code == 204
    assert client.get(f"{J}/entries/{one}", headers=ada).status_code == 404
    assert client.post(f"{J}/delete-all", json={"confirm": False}, headers=ada).status_code == 422
    assert client.post(f"{J}/delete-all", json={"confirm": True}, headers=ada).status_code == 204
    assert client.get(f"{J}/entries", headers=ada).json()["items"] == []

    _new(client, ada, body="After")
    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204
    with db(client) as s:
        assert s.scalars(select(JournalEntry)).all() == []


def test_journal_text_is_never_logged(client, caplog):
    ada = signup(client)
    with caplog.at_level("DEBUG"):
        e = _new(client, ada, body="zebra-unique-phrase")
        client.post(f"{J}/search", json={"q": "zebra-unique-phrase"}, headers=ada)
        client.patch(f"{J}/entries/{e['id']}", json={"body": "zebra-unique-phrase 2"}, headers=ada)
    assert "zebra-unique-phrase" not in caplog.text
