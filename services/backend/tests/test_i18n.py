"""Languages: one registry, only released languages selectable, and translated instruments need review."""

import json

import pytest
from pydantic import ValidationError

from app.assessments.content import Instrument
from app.i18n.locales import LocaleRegistry, load_locales
from tests.conftest import CONTENT_DIR
from tests.test_admin import A, _grant
from tests.test_auth import signup


def test_registry_and_negotiation():
    reg = load_locales()
    assert reg.default == "en" and [x.code for x in reg.released()] == ["en"]
    assert {x.code for x in reg.locales} == {"en", "es", "am", "fr", "de", "ar", "pt", "hi", "zh", "ja"}
    assert reg.get("ar").direction == "rtl"
    assert reg.negotiate("fr-CA,fr;q=0.9,en-GB;q=0.8") == "en"
    assert (
        reg.negotiate("de;q=0,xx") == "en"
        and reg.negotiate(None) == "en"
        and reg.negotiate("en;q=bad") == "en"
    )
    raw = reg.model_dump()
    with pytest.raises(ValidationError):
        LocaleRegistry.model_validate({**raw, "default": "es"})  # not released
    with pytest.raises(ValidationError):
        LocaleRegistry.model_validate({**raw, "locales": raw["locales"] + raw["locales"][:1]})


def test_public_list_and_profile_language(client):
    body = client.get("/api/v1/locales").json()
    assert body["default"] == "en" and len(body["locales"]) == 10 and "docs/LOCALIZATION.md" in body["note"]
    ada = signup(client)
    assert client.patch("/api/v1/me", json={"locale": "en"}, headers=ada).json()["locale"] == "en"
    for code in ("es", "xx"):
        r = client.patch("/api/v1/me", json={"locale": code}, headers=ada)
        assert r.status_code == 422 and r.json()["error"]["code"] == "locale_unavailable"


def test_translated_instruments_need_an_approved_adaptation():
    raw = json.loads((CONTENT_DIR / "instruments" / "mini-ipip-20.v1.0.0.json").read_text(encoding="utf-8"))
    spanish = {**raw, "locale": "es"}
    with pytest.raises(ValidationError, match="adaptation record"):
        Instrument.model_validate(spanish)
    review = {"source_instrument": "mini-ipip-20@1.0.0", "method": "team_translation", "status": "in_review"}
    with pytest.raises(ValidationError, match="approved review"):
        Instrument.model_validate({**spanish, "adaptation": review})
    assert Instrument.model_validate({**spanish, "status": "draft", "adaptation": review}).adaptation
    approved = {**review, "status": "approved", "reviewers": ["Bilingual psychometrician"]}
    assert Instrument.model_validate({**spanish, "adaptation": approved}).locale == "es"


def test_admin_content_lists_languages(client):
    root = signup(client, "root@example.com")
    _grant(client, root, "content")
    c = client.get(f"{A}/content", headers=root).json()
    assert [x["code"] for x in c["languages"] if x["status"] == "released"] == ["en"]
    assert all(i["locale"] == "en" and i["adaptation"] is None for i in c["instruments"])
