"""Share cards: opt-in, minimal public data, revocation, ownership and cleanup."""

from sqlalchemy import select

from app.database.models import ShareCard
from app.reports.schemas import ReportBody
from app.sharing.card import build_card, render_svg
from tests.test_auth import PASSWORD, db, signup
from tests.test_reports import R, _big_five

S = "/api/v1/share-cards"
P = "/api/v1/public/cards"


def _report(client, h):
    _big_five(client, h)
    r = client.post(R, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_card_holds_no_scores_and_svg_is_safe(client):
    ada = signup(client)
    body = ReportBody.model_validate(_report(client, ada)["body"])
    card = build_card(body, "27 November 2026", include_archetype=True, include_traits=True)
    assert card.archetype == body.profile.name and len(card.traits) == 5
    assert "score" not in card.model_dump_json()
    assert build_card(body, "x", include_archetype=False, include_traits=True).archetype is None
    assert build_card(body, "x", include_archetype=True, include_traits=False).traits == []

    svg = render_svg(card.model_copy(update={"archetype": "<script>alert(1)</script> & co"}))
    assert svg.startswith("<svg") and "<script>" not in svg and "&lt;script&gt;" in svg
    assert 'role="img"' in svg and "<title" in svg and "<desc" in svg


def test_share_view_and_revoke(client):
    ada = signup(client)
    rep = _report(client, ada)
    r = client.post(S, json={"report_id": rep["id"]}, headers=ada)
    assert r.status_code == 201, r.text
    card = r.json()
    token = card["token"]
    assert card["card"]["archetype"] == rep["body"]["profile"]["name"]
    assert [t["band"] for t in card["card"]["traits"]] == [t["band"] for t in rep["body"]["traits"]]

    # Public: no sign-in, no caching, not indexed, no name or email.
    client.cookies.clear()
    pub = client.get(f"{P}/{token}")
    assert pub.status_code == 200 and pub.json() == card["card"]
    assert pub.headers["cache-control"] == "no-store" and "noindex" in pub.headers["x-robots-tag"]
    assert "ada@example.com" not in pub.text
    img = client.get(f"{P}/{token}/image.svg")
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/svg+xml")
    assert "default-src 'none'" in img.headers["content-security-policy"]

    # The owner can see the link again; only the hash is used for lookup.
    assert client.get(S, headers=ada).json()["cards"] == [card]
    with db(client) as s:
        row = s.scalars(select(ShareCard)).one()
        assert token not in row.token_encrypted and row.token_hash != token

    assert client.delete(f"{S}/{card['id']}", headers=ada).status_code == 204
    assert client.get(f"{P}/{token}").status_code == 404
    assert client.get(f"{P}/{token}/image.svg").status_code == 404
    assert client.get(f"{P}/not-a-real-token").status_code == 404


def test_choices_limits_and_ownership(client, monkeypatch):
    ada = signup(client)
    rep = _report(client, ada)
    r = client.post(S, json={"report_id": rep["id"], "include_archetype": False}, headers=ada)
    assert r.json()["card"]["archetype"] is None and r.json()["card"]["summary"] is None
    r = client.post(
        S, json={"report_id": rep["id"], "include_archetype": False, "include_traits": False}, headers=ada
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_card"

    monkeypatch.setattr("app.sharing.service.MAX_CARDS", 1)
    r = client.post(S, json={"report_id": rep["id"]}, headers=ada)
    assert r.status_code == 409 and r.json()["error"]["code"] == "too_many_cards"
    monkeypatch.undo()

    client.cookies.clear()
    bob = signup(client, "bob@example.com")
    assert client.post(S, json={"report_id": rep["id"]}, headers=bob).status_code == 404
    mine = client.get(S, headers=ada).json()["cards"][0]["id"]
    assert client.delete(f"{S}/{mine}", headers=bob).status_code == 404
    assert client.get(S, headers=bob).json() == {"cards": []}


def test_deleting_report_or_account_removes_cards(client):
    ada = signup(client)
    rep = _report(client, ada)
    token = client.post(S, json={"report_id": rep["id"]}, headers=ada).json()["token"]
    assert client.delete(f"{R}/{rep['id']}", headers=ada).status_code == 204
    assert client.get(f"{P}/{token}").status_code == 404

    rep = client.post(R, headers=ada).json()
    card = client.post(S, json={"report_id": rep["id"]}, headers=ada).json()
    assert client.get("/api/v1/privacy/export", headers=ada).json()["share_cards"] == [card]
    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=ada)
    assert r.status_code == 204
    assert client.get(f"{P}/{card['token']}").status_code == 404
    with db(client) as s:
        assert s.scalars(select(ShareCard)).all() == []
