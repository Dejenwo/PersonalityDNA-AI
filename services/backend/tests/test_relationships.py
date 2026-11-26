import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.database.models import RelationshipInvitation, RelationshipLink
from app.relationships.compare import compare, pattern_for
from app.security.consent import RELATIONSHIP_POLICY_VERSION
from tests.test_auth import PASSWORD, _complete, db, signup

CONSENT = {"accepted": True, "policy_version": RELATIONSHIP_POLICY_VERSION}
TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "emotional_stability"]


# ---------- comparison (pure) ----------


def test_patterns():
    assert pattern_for("higher", "higher") == "similar"
    assert pattern_for("middle", "middle") == "similar"
    assert pattern_for("lower", "higher") == "different"
    assert pattern_for("middle", "lower") == "some_difference"
    assert pattern_for("higher", "middle") == "some_difference"


def test_compare_texts(content):
    insights = content.relationships.data
    names = {t: x.name for t, x in content.interpretations.data.traits.items()}
    you = {
        "extraversion": "higher",
        "openness": "middle",
        "agreeableness": "lower",
        "conscientiousness": "higher",
    }
    them = {
        "extraversion": "lower",
        "openness": "middle",
        "agreeableness": "middle",
        "conscientiousness": "higher",
    }
    you["emotional_stability"] = None  # unscored traits are left out
    them["emotional_stability"] = "higher"
    out = {c.trait: c for c in compare(insights, names, you, them)}
    assert set(out) == {"openness", "conscientiousness", "extraversion", "agreeableness"}

    ext = out["extraversion"]
    assert ext.pattern == "different" and ext.misunderstanding
    assert ext.summary == (
        "You tend to recharge through company and like to talk things through, "
        "while they tend to recharge through quiet time and like to think before speaking."
    )
    assert out["openness"].summary == "You both sit in the middle here."
    assert out["conscientiousness"].summary.startswith("You both tend to like plans")
    assert out["conscientiousness"].misunderstanding is None
    assert out["agreeableness"].pattern == "some_difference"
    assert out["agreeableness"].summary.endswith("while they are in the middle.")

    # The same pair seen from the other side.
    flipped = {c.trait: c for c in compare(insights, names, them, you)}
    assert flipped["agreeableness"].summary.startswith("They tend to")
    assert flipped["agreeableness"].summary.endswith("while you are in the middle.")


def test_content_has_no_scores_or_predictions(content):
    text = json.dumps(content.relationships.data.model_dump()).lower()
    for banned in ("%", "compatib", "percentile", "will last", "break up", "divorce", "diagnos"):
        assert banned not in text


# ---------- API ----------


def _with_result(client, email):
    h = signup(client, email)
    s = client.post(
        "/api/v1/assessment-sessions",
        headers=h,
        json={
            "instrument_id": "mini-ipip-20",
            "consent": {"accepted": True, "age_confirmed_18_plus": True, "policy_version": "2026-11-26"},
        },
    ).json()
    _complete(client, s["session"]["id"], h)
    return h


def _invite(client, h, relation="partner"):
    r = client.post(
        "/api/v1/relationships/invitations", json={"relation_type": relation, "consent": CONSENT}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_invite_accept_compare_and_revoke(client):
    ada = _with_result(client, "ada@example.com")
    client.patch("/api/v1/me", json={"display_name": "Ada"}, headers=ada)
    bob = signup(client, "bob@example.com")
    eve = signup(client, "eve@example.com")

    created = _invite(client, ada)
    token = created["token"]
    assert (
        client.get("/api/v1/relationships", headers=ada).json()["invitations"][0]["id"]
        == (created["invitation"]["id"])
    )
    with db(client) as s:  # only the hash is stored
        assert s.query(RelationshipInvitation).one().token_hash != token

    r = client.post("/api/v1/relationships/invitations/preview", json={"token": token}, headers=bob)
    assert r.json() == {
        "inviter_name": "Ada",
        "relation_type": "partner",
        "expires_at": created["invitation"]["expires_at"],
        "policy_version": RELATIONSHIP_POLICY_VERSION,
    }
    # The inviter cannot accept their own link; consent must be current.
    own = client.post(
        "/api/v1/relationships/invitations/accept", json={"token": token, "consent": CONSENT}, headers=ada
    )
    assert own.status_code == 409 and own.json()["error"]["code"] == "own_invitation"
    old = client.post(
        "/api/v1/relationships/invitations/accept",
        json={"token": token, "consent": {**CONSENT, "policy_version": "2020-01-01"}},
        headers=bob,
    )
    assert old.status_code == 409 and old.json()["error"]["code"] == "consent_outdated"
    no_consent = client.post("/api/v1/relationships/invitations/accept", json={"token": token}, headers=bob)
    assert no_consent.status_code == 422

    r = client.post(
        "/api/v1/relationships/invitations/accept", json={"token": token, "consent": CONSENT}, headers=bob
    )
    assert r.status_code == 201, r.text
    link = r.json()
    assert link["other_name"] == "Ada" and link["you_invited"] is False
    # Single use: the invitation is gone.
    again = client.post(
        "/api/v1/relationships/invitations/accept", json={"token": token, "consent": CONSENT}, headers=eve
    )
    assert again.status_code == 404
    assert client.get("/api/v1/relationships", headers=ada).json()["invitations"] == []

    # Bob has no result yet, so there is nothing to compare.
    d = client.get(f"/api/v1/relationships/{link['id']}", headers=ada).json()
    assert d["missing_results"] == ["them"] and d["traits"] == [] and d["you_invited"] is True
    assert d["exercises"] and d["shared_goals"] and "not predictions" in d["note"]

    _complete_for(client, bob)
    a = client.get(f"/api/v1/relationships/{link['id']}", headers=ada).json()
    b = client.get(f"/api/v1/relationships/{link['id']}", headers=bob).json()
    assert a["missing_results"] == [] and [t["trait"] for t in a["traits"]] == TRAITS
    assert [(t["you"], t["them"]) for t in a["traits"]] == [(t["them"], t["you"]) for t in b["traits"]]
    # Bands only: no numeric scores, answers or percentages are shared.
    raw = json.dumps(a)
    assert '"score"' not in raw and '"answers"' not in raw and "%" not in raw

    # Strangers see nothing.
    assert client.get(f"/api/v1/relationships/{link['id']}", headers=eve).status_code == 404
    assert client.delete(f"/api/v1/relationships/{link['id']}", headers=eve).status_code == 404

    # Either person can revoke, which ends it for both.
    assert client.delete(f"/api/v1/relationships/{link['id']}", headers=bob).status_code == 204
    assert client.get(f"/api/v1/relationships/{link['id']}", headers=ada).status_code == 404
    assert client.get("/api/v1/relationships", headers=ada).json()["links"] == []


def _complete_for(client, h):
    s = client.post(
        "/api/v1/assessment-sessions",
        headers=h,
        json={
            "instrument_id": "mini-ipip-20",
            "consent": {"accepted": True, "age_confirmed_18_plus": True, "policy_version": "2026-11-26"},
        },
    ).json()
    items = client.get("/api/v1/assessments/mini-ipip-20").json()["items"]
    client.put(
        f"/api/v1/assessment-sessions/{s['session']['id']}/answers",
        json={"answers": [{"item_id": i["id"], "value": 5 - (n % 3)} for n, i in enumerate(items)]},
        headers=h,
    )
    assert (
        client.post(f"/api/v1/assessment-sessions/{s['session']['id']}/complete", headers=h).status_code
        == 200
    )


def test_one_link_per_pair_cancel_expiry_and_limit(client):
    ada = signup(client, "ada@example.com")
    bob = signup(client, "bob@example.com")
    first = _invite(client, ada)["token"]
    accept = {"consent": CONSENT}
    assert (
        client.post("/api/v1/relationships/invitations/accept", json={"token": first, **accept}, headers=bob)
    ).status_code == 201
    reverse = _invite(client, bob, "friend")["token"]
    dup = client.post(
        "/api/v1/relationships/invitations/accept", json={"token": reverse, **accept}, headers=ada
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "already_linked"

    # Cancel.
    inv = _invite(client, ada, "colleague")
    assert (
        client.delete(f"/api/v1/relationships/invitations/{inv['invitation']['id']}", headers=bob).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/relationships/invitations/{inv['invitation']['id']}", headers=ada).status_code
        == 204
    )
    assert (
        client.post("/api/v1/relationships/invitations/preview", json={"token": inv["token"]}, headers=bob)
    ).status_code == 404

    # Expiry.
    expiring = _invite(client, ada, "family")
    with db(client) as s:
        row = s.get(RelationshipInvitation, uuid.UUID(expiring["invitation"]["id"]))
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        s.commit()
    r = client.post(
        "/api/v1/relationships/invitations/preview", json={"token": expiring["token"]}, headers=bob
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "invitation_not_found"

    # At most 10 open invitations (bob has one open already).
    for _ in range(9):
        _invite(client, bob)
    r = client.post(
        "/api/v1/relationships/invitations", json={"relation_type": "friend", "consent": CONSENT}, headers=bob
    )
    assert r.status_code == 429 and r.json()["error"]["code"] == "too_many_invitations"


@pytest.mark.parametrize("body", [{"relation_type": "boss", "consent": CONSENT}, {"relation_type": "friend"}])
def test_invitation_validation(client, body):
    ada = signup(client)
    assert client.post("/api/v1/relationships/invitations", json=body, headers=ada).status_code == 422


def test_requires_sign_in(client):
    assert client.get("/api/v1/relationships").status_code == 401


def test_export_and_account_deletion(client):
    ada = signup(client, "ada@example.com")
    bob = signup(client, "bob@example.com")
    token = _invite(client, ada)["token"]
    client.post(
        "/api/v1/relationships/invitations/accept", json={"token": token, "consent": CONSENT}, headers=bob
    )
    export = client.get("/api/v1/privacy/export", headers=bob).json()
    assert export["relationships"]["links"][0]["relation_type"] == "partner"
    assert any(c["type"] == "relationship_sharing" for c in export["consents"])

    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204
    with db(client) as s:
        assert s.query(RelationshipLink).count() == 0
    assert client.get("/api/v1/relationships", headers=bob).json()["links"] == []
