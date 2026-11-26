import json
import shutil
from pathlib import Path

import pytest

from app.assessments.content import ContentError, load_content
from tests.conftest import CONTENT_DIR

IPIP_50_KEYS = {
    # From https://ipip.ori.org/New_IPIP-50-item-scale.htm (checked 2026-11-26): item number -> (factor, key)
    "extraversion": {1: "+", 6: "-", 11: "+", 16: "-", 21: "+", 26: "-", 31: "+", 36: "-", 41: "+", 46: "-"},
    "agreeableness": {2: "-", 7: "+", 12: "-", 17: "+", 22: "-", 27: "+", 32: "-", 37: "+", 42: "+", 47: "+"},
    "conscientiousness": {
        3: "+",
        8: "-",
        13: "+",
        18: "-",
        23: "+",
        28: "-",
        33: "+",
        38: "-",
        43: "+",
        48: "+",
    },
    "emotional_stability": {
        4: "-",
        9: "+",
        14: "-",
        19: "+",
        24: "-",
        29: "-",
        34: "-",
        39: "-",
        44: "-",
        49: "-",
    },
    "openness": {5: "+", 10: "-", 15: "+", 20: "-", 25: "+", 30: "-", 35: "+", 40: "+", 45: "+", 50: "+"},
}


def test_bfm50_matches_published_keying(content):
    inst = content.instrument("ipip-bfm-50", "1.0.0").data
    assert len(inst.items) == 50
    for item in inst.items:
        assert IPIP_50_KEYS[item.scale][item.number] == item.keyed, item


def test_mini_ipip_structure(content):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    assert len(inst.items) == 20
    for scale in inst.scales:
        items = [i for i in inst.items if i.scale == scale.id]
        assert len(items) == 4
    # Mini-IPIP items are a subset of IPIP wording used in the 50-item markers or IPIP pool.
    bfm_text = {i.text for i in content.instrument("ipip-bfm-50", "1.0.0").data.items}
    assert all(i.text in bfm_text for i in inst.items)


def test_every_instrument_has_licence_record(content):
    for loaded in content.instruments.values():
        assert (CONTENT_DIR / loaded.data.license.file).is_file()


def _copy(tmp_path: Path) -> Path:
    dst = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, dst)
    return dst


def test_missing_licence_is_rejected(tmp_path):
    dst = _copy(tmp_path)
    (dst / "licenses" / "IPIP.md").unlink()
    with pytest.raises(ContentError, match="licence"):
        load_content(dst)


def test_bad_keying_value_is_rejected(tmp_path):
    dst = _copy(tmp_path)
    path = dst / "instruments" / "mini-ipip-20.v1.0.0.json"
    data = json.loads(path.read_text())
    data["items"][0]["keyed"] = "?"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_content(dst)


def test_misnamed_file_is_rejected(tmp_path):
    dst = _copy(tmp_path)
    src = dst / "instruments" / "mini-ipip-20.v1.0.0.json"
    src.rename(dst / "instruments" / "mini.json")
    with pytest.raises(ContentError, match="must be named"):
        load_content(dst)
