"""Organisations: voluntary membership, least-privilege roles, seat licences, programmes and suppressed
aggregates that never expose an individual's results."""

import uuid
from collections import Counter

from sqlalchemy import select

from app.database.models import AuditEvent, ConsentRecord, Organization, OrgProgramParticipant
from app.organizations import service
from app.security.consent import ORG_POLICY_VERSION
from tests.test_admin import A, _grant
from tests.test_auth import PASSWORD, db, signup
from tests.test_reports import _big_five

ORGS = "/api/v1/orgs"
CONSENT = {"accepted": True, "policy_version": ORG_POLICY_VERSION}


def _org(client, h, name="Acme Learning"):
    r = client.post(ORGS, json={"name": name, "consent": CONSENT}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _invite(client, h, org_id, **body):
    r = client.post(f"{ORGS}/{org_id}/invitations", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["token"]


def _join(client, h, token):
    return client.post(f"{ORGS}/invitations/accept", json={"token": token, "consent": CONSENT}, headers=h)


def _person(client, email):
    client.cookies.clear()
    return signup(client, email)


def test_create_invite_join_and_roles(client):
    owner = signup(client, "owner@example.com")
    org = _org(client, owner, "  Acme   Learning ")
    assert org["name"] == "Acme Learning" and org["role"] == "owner"
    assert org["licence"] == {
        "licence": "pilot",
        "seat_limit": service.PILOT_SEATS,
        "seats_used": 1,
        "licensed_until": None,
        "active": False,
    }
    stale = {"accepted": True, "policy_version": "2000-01-01"}
    assert client.post(ORGS, json={"name": "X org", "consent": stale}, headers=owner).status_code == 409
    assert client.get(ORGS).status_code == 401

    token = _invite(client, owner, org["id"], max_uses=2)
    ada = _person(client, "ada@example.com")
    preview = client.post(f"{ORGS}/invitations/preview", json={"token": token}, headers=ada).json()
    assert preview["organisation"] == "Acme Learning" and preview["role"] == "member"
    assert not preview["already_member"]
    joined = _join(client, ada, token)
    assert joined.status_code == 200 and joined.json()["role"] == "member"
    assert _join(client, ada, token).json()["error"]["code"] == "already_member"
    assert [o["name"] for o in client.get(ORGS, headers=ada).json()["organisations"]] == ["Acme Learning"]

    # Members can't manage; non-members can't see the organisation at all.
    for path in ("/members", "/invitations", "/analytics"):
        assert client.get(f"{ORGS}/{org['id']}{path}", headers=ada).status_code == 403
    bob = _person(client, "bob@example.com")
    for path in ("", "/members", "/programs", "/analytics"):
        assert client.get(f"{ORGS}/{org['id']}{path}", headers=bob).status_code == 404
    # The second use of the link is Bob's; then it's used up.
    assert _join(client, bob, token).status_code == 200
    carol = _person(client, "carol@example.com")
    assert _join(client, carol, token).status_code == 404

    # Owners see names and emails only: no results, no sharing choices.
    members = client.get(f"{ORGS}/{org['id']}/members", headers=owner).json()["members"]
    assert [m["email"] for m in members] == ["owner@example.com", "ada@example.com", "bob@example.com"]
    assert set(members[0]) == {"id", "display_name", "email", "role", "joined_at"}
    ada_m, bob_m = members[1]["id"], members[2]["id"]

    # Admins can remove members but not other admins, and can't invite admins or change roles.
    r = client.put(f"{ORGS}/{org['id']}/members/{ada_m}/role", json={"role": "admin"}, headers=owner)
    assert [m["role"] for m in r.json()["members"]] == ["owner", "admin", "member"]
    assert (
        client.post(f"{ORGS}/{org['id']}/invitations", json={"role": "admin"}, headers=ada).status_code == 403
    )
    assert (
        client.put(
            f"{ORGS}/{org['id']}/members/{bob_m}/role", json={"role": "admin"}, headers=ada
        ).status_code
        == 403
    )
    owner_m = members[0]["id"]
    assert client.delete(f"{ORGS}/{org['id']}/members/{owner_m}", headers=ada).status_code == 403
    assert client.delete(f"{ORGS}/{org['id']}/members/{bob_m}", headers=ada).status_code == 204
    assert client.get(f"{ORGS}/{org['id']}", headers=bob).status_code == 404

    # There is always an owner.
    r = client.put(f"{ORGS}/{org['id']}/members/{owner_m}/role", json={"role": "member"}, headers=owner)
    assert r.status_code == 409 and r.json()["error"]["code"] == "last_owner"
    assert client.delete(f"{ORGS}/{org['id']}/membership", headers=owner).status_code == 409
    assert client.delete(f"{ORGS}/{org['id']}/membership", headers=ada).status_code == 204

    # Rename, list and cancel invitations, delete.
    assert client.patch(f"{ORGS}/{org['id']}", json={"name": "Acme"}, headers=owner).json()["name"] == "Acme"
    _invite(client, owner, org["id"])
    inv = client.get(f"{ORGS}/{org['id']}/invitations", headers=owner).json()["invitations"]
    assert len(inv) == 1 and inv[0]["uses"] == 0
    assert client.delete(f"{ORGS}/{org['id']}/invitations/{inv[0]['id']}", headers=owner).status_code == 204
    assert client.delete(f"{ORGS}/{org['id']}", headers=owner).status_code == 204
    assert client.get(ORGS, headers=owner).json()["organisations"] == []

    with db(client) as s:
        kinds = {e.event_type for e in s.scalars(select(AuditEvent)) if e.event_type.startswith("org.")}
        assert {"org.created", "org.member_joined", "org.role_changed", "org.member_removed"} <= kinds
        consents = [c.consent_type for c in s.scalars(select(ConsentRecord))]
        assert consents.count("organisation_membership") == 3


def test_seat_limit_and_licence_gives_premium(client):
    owner = signup(client, "owner@example.com")
    org = _org(client, owner)
    with db(client) as s:
        s.get(Organization, uuid.UUID(org["id"])).seat_limit = 2
        s.commit()
    token = _invite(client, owner, org["id"], max_uses=5)
    ada = _person(client, "ada@example.com")
    assert _join(client, ada, token).status_code == 200
    bob = _person(client, "bob@example.com")
    r = _join(client, bob, token)
    assert r.status_code == 409 and r.json()["error"]["code"] == "seat_limit"
    assert client.get("/api/v1/billing/me", headers=ada).json()["plan_id"] == "free"

    # A superadmin records a licence; members then get the organisation plan.
    root = _person(client, "root@example.com")
    _grant(client, root, "superadmin")
    found = client.get(f"{A}/organisations", params={"q": "acme"}, headers=root).json()["organisations"]
    assert [(o["name"], o["members"], o["owners"]) for o in found] == [("Acme Learning", 2, 1)]
    body = {"licence": "licensed", "seat_limit": 3, "reason": "Signed pilot agreement"}
    assert client.put(f"{A}/organisations/{org['id']}/licence", json=body, headers=root).status_code == 422
    r = client.put(f"{A}/organisations/{org['id']}/licence", json={**body, "days": 365}, headers=root)
    assert r.json()["licence_active"] is True and r.json()["seat_limit"] == 3
    me = client.get("/api/v1/billing/me", headers=ada).json()
    assert me["plan_id"] == "organisation" and me["subscription"] is None
    assert client.get(f"{ORGS}/{org['id']}", headers=ada).json()["licence"]["active"] is True
    assert _join(client, bob, token).status_code == 200

    # Support can look organisations up but not change licences.
    sam = _person(client, "sam@example.com")
    _grant(client, sam, "support")
    assert client.get(f"{A}/organisations", headers=sam).status_code == 200
    assert client.put(f"{A}/organisations/{org['id']}/licence", json=body, headers=sam).status_code == 404

    # Back to a pilot: Premium ends.
    pilot = {"licence": "pilot", "seat_limit": 3, "reason": "Agreement ended"}
    client.put(f"{A}/organisations/{org['id']}/licence", json=pilot, headers=root)
    assert client.get("/api/v1/billing/me", headers=ada).json()["plan_id"] == "free"
    with db(client) as s:
        assert [
            e.details["admin_id"]
            for e in s.scalars(select(AuditEvent))
            if e.event_type == "admin.org_licence"
        ]


def test_programmes_are_voluntary(client):
    owner = signup(client, "owner@example.com")
    org = _org(client, owner)
    cat = client.get(f"{ORGS}/catalog", headers=owner).json()
    gp = cat["growth_programs"][0]["id"]
    module = cat["leadership"][0]["id"]
    base = f"{ORGS}/{org['id']}/programs"
    assert client.post(base, json={"title": "Empty"}, headers=owner).status_code == 422
    assert (
        client.post(base, json={"title": "Bad", "growth_program_id": "nope"}, headers=owner).status_code
        == 422
    )
    r = client.post(
        base,
        json={
            "title": "Spring cohort",
            "description": "Optional.",
            "growth_program_id": gp,
            "learning": [{"track": "leadership", "module": module}],
        },
        headers=owner,
    )
    assert r.status_code == 201, r.text
    prog = r.json()
    assert [i["href"] for i in prog["items"]] == [f"/growth/{gp}", f"/leadership/{module}"]

    ada = _person(client, "ada@example.com")
    assert _join(client, ada, _invite(client, owner, org["id"])).status_code == 200
    assert client.post(base, json={"title": "Mine", "growth_program_id": gp}, headers=ada).status_code == 403
    assert client.put(f"{base}/{prog['id']}/participation", headers=ada).json()["joined"] is True
    assert client.get(base, headers=ada).json()["programs"][0]["joined"] is True
    # One participant is below the cell threshold, so the count is hidden.
    a = client.get(f"{ORGS}/{org['id']}/analytics", headers=owner).json()
    assert a["programs"] == [{"id": prog["id"], "title": "Spring cohort", "participants": None}]
    assert client.delete(f"{base}/{prog['id']}/participation", headers=ada).json()["joined"] is False

    # Leaving the organisation removes participation; deleting the programme is for managers.
    client.put(f"{base}/{prog['id']}/participation", headers=ada)
    assert client.delete(f"{base}/{prog['id']}", headers=ada).status_code == 403
    client.delete(f"{ORGS}/{org['id']}/membership", headers=ada)
    with db(client) as s:
        assert s.scalars(select(OrgProgramParticipant)).all() == []
    assert client.delete(f"{base}/{prog['id']}", headers=owner).status_code == 204


def test_suppression_rules():
    assert service.suppress(Counter(lower=3, middle=4, higher=3)).model_dump() == {
        "lower": 3,
        "middle": 4,
        "higher": 3,
    }
    # Any band under the threshold hides the whole trait, including empty bands.
    assert service.suppress(Counter(lower=2, middle=5, higher=5)) is None
    assert service.suppress(Counter(middle=10)) is None


def test_analytics_only_from_opted_in_members_and_large_groups(client, monkeypatch):
    owner = signup(client, "owner@example.com")
    org = _org(client, owner)
    token = _invite(client, owner, org["id"], max_uses=10)
    people = []
    for i in range(3):
        h = _person(client, f"p{i}@example.com")
        _big_five(client, h)
        assert _join(client, h, token).status_code == 200
        people.append(h)
    url = f"{ORGS}/{org['id']}/analytics"
    a = client.get(url, headers=owner).json()
    assert a["members"] == 4 and a["consenting_members"] is None and a["traits"] == []
    assert "hiring" in a["note"]

    # Opting in is each member's own choice and is recorded as consent.
    for h in people:
        r = client.put(f"{ORGS}/{org['id']}/membership/sharing", json={"share_aggregates": True}, headers=h)
        assert r.json()["share_aggregates"] is True
    a = client.get(url, headers=owner).json()
    assert a["consenting_members"] is None and a["traits"] == []  # 3 is under the group minimum of 10

    # With lower thresholds the same data shows: everyone answered identically, so every trait sits in a
    # single band and stays suppressed under the default cell size, but appears with a cell size of 1.
    monkeypatch.setattr(service, "MIN_GROUP", 3)
    a = client.get(url, headers=owner).json()
    assert a["consenting_members"] == 3 and len(a["traits"]) == 5
    assert all(t["bands"] is None for t in a["traits"])
    monkeypatch.setattr(service, "MIN_CELL", 0)
    a = client.get(url, headers=owner).json()
    assert all(sum(t["bands"].values()) == 3 for t in a["traits"])

    # Opting out removes a member straight away.
    client.put(f"{ORGS}/{org['id']}/membership/sharing", json={"share_aggregates": False}, headers=people[0])
    assert client.get(url, headers=owner).json()["consenting_members"] is None
    with db(client) as s:
        kinds = [(c.consent_type, c.granted) for c in s.scalars(select(ConsentRecord))]
        assert kinds.count(("organisation_aggregates", True)) == 3
        assert kinds.count(("organisation_aggregates", False)) == 1
    # No individual result ever appears in the response.
    text = client.get(url, headers=owner).text
    assert "p0@example.com" not in text and "score" not in text


def test_export_and_account_deletion_hand_over_ownership(client):
    owner = signup(client, "owner@example.com")
    org = _org(client, owner)
    solo = _org(client, owner, "Solo team")
    ada = _person(client, "ada@example.com")
    _join(client, ada, _invite(client, owner, org["id"]))
    bob = _person(client, "bob@example.com")
    _join(client, bob, _invite(client, owner, org["id"], role="admin"))

    exported = client.get("/api/v1/privacy/export", headers=ada).json()["organisations"]
    assert [(o["name"], o["role"]) for o in exported] == [("Acme Learning", "member")]

    r = client.request("DELETE", "/api/v1/account", json={"password": PASSWORD}, headers=owner)
    assert r.status_code == 204
    # The admin (not the earlier-joined member) becomes owner; the one-person organisation is gone.
    assert client.get(f"{ORGS}/{org['id']}", headers=bob).json()["role"] == "owner"
    with db(client) as s:
        assert s.get(Organization, uuid.UUID(solo["id"])) is None
