"""Learning tracks: the emotional awareness track and behaviour shared by all tracks."""

from tests.test_auth import signup

EA = "/api/v1/learning/emotional-awareness"
EA_MODULES = [
    "naming-feelings",
    "pause-and-reflect",
    "listening-to-understand",
    "perspective-taking",
    "everyday-stress",
    "reading-the-room",
    "expressing-constructively",
]


def test_emotional_awareness_content(content):
    track = content.track("emotional-awareness")
    assert track is not None and track is content.emotional_awareness.data
    assert [m.id for m in track.modules] == EA_MODULES
    assert all(len(m.activities) >= 2 and len(m.lessons) >= 2 and m.reflection for m in track.modules)
    assert "not therapy" in track.note and "no emotional intelligence score" in track.note
    assert track.support_note and "988" in track.support_note
    assert content.track("leadership") is content.leadership.data
    assert content.track("nope") is None
    # Nothing in the track reads as a diagnosis or a score.
    text = track.model_dump_json().lower()
    for word in ("diagnos", "disorder", "your eq", "ei score", "percentile"):
        assert word not in text.replace("nothing here diagnoses anything", "")


def test_track_listing_and_module(client):
    assert client.get("/api/v1/learning/nope/modules").status_code == 404
    listing = client.get(f"{EA}/modules").json()
    assert listing["track"] == "emotional-awareness" and listing["title"] == "Emotional awareness"
    assert "988" in listing["support_note"]
    assert [m["id"] for m in listing["modules"]] == EA_MODULES
    assert all(m["activities_done"] == 0 and m["reason"] is None for m in listing["modules"])
    module = client.get(f"{EA}/modules/naming-feelings").json()
    assert module["track_title"] == "Emotional awareness" and module["area"] == "self-awareness"
    assert [a["id"] for a in module["activities"]] == ["three-check-ins", "word-swap"]
    # A module from another track is not found under this one.
    assert client.get(f"{EA}/modules/delegation").status_code == 404
    lead = client.get("/api/v1/learning/leadership/modules").json()
    assert lead["title"] == "Leadership development" and lead["support_note"] is None


def test_progress_is_per_track_and_per_user(client):
    ada = signup(client)
    url = f"{EA}/modules/naming-feelings/activities/word-swap/done"
    assert client.put(url).status_code == 401
    assert client.put(url, headers=ada).status_code == 204
    assert (
        client.put(f"{EA}/modules/naming-feelings/activities/handover/done", headers=ada).status_code == 404
    )
    assert (
        client.put(
            "/api/v1/learning/nope/modules/naming-feelings/activities/word-swap/done", headers=ada
        ).status_code
        == 404
    )
    done = {m["id"]: m["activities_done"] for m in client.get(f"{EA}/modules", headers=ada).json()["modules"]}
    assert done["naming-feelings"] == 1 and sum(done.values()) == 1
    lead = client.get("/api/v1/learning/leadership/modules", headers=ada).json()["modules"]
    assert sum(m["activities_done"] for m in lead) == 0
    bob = signup(client, "bob@example.com")
    assert sum(m["activities_done"] for m in client.get(f"{EA}/modules", headers=bob).json()["modules"]) == 0

    export = client.get("/api/v1/privacy/export", headers=ada).json()["learning_activities"]
    assert [(e["track"], e["module"], e["activity"]) for e in export] == [
        ("emotional-awareness", "naming-feelings", "word-swap")
    ]
    assert client.delete(url, headers=ada).status_code == 204
    assert (
        client.get(f"{EA}/modules/naming-feelings", headers=ada).json()["activities"][1]["completed_at"]
        is None
    )


def test_emotions_coach_topic(client):
    from tests.test_coach import CONSENT

    ada = signup(client)
    conv = client.post(
        "/api/v1/coach/conversations", json={"consent": CONSENT, "topic": "emotions"}, headers=ada
    )
    assert conv.status_code == 201, conv.text
    assert conv.json()["title"] == "Emotions and communication"
