"""Regression snapshots: fixed answers for every instrument produce exactly the stored result.

A change to scoring, bands, archetypes or interpretation text fails here. If the change is intended (and
ENGINE_VERSION or the content version was bumped where required), regenerate with

    PDNA_UPDATE_GOLDEN=1 pytest tests/test_golden.py

and review the JSON diff by hand before committing it.
"""

import json
import os
import re
from pathlib import Path

import pytest

from tests.conftest import start

GOLDEN = Path(__file__).parent / "golden"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
INSTRUMENTS = ["mini-ipip-20", "ipip-bfm-50", "onet-ipsf-60", "leadership-preferences-27"]


def _scrub(value):
    """Replace ids and timestamps, which differ on every run."""
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str) and UUID.match(value):
        return "<id>"
    if isinstance(value, str) and TIME.match(value):
        return "<time>"
    return value


def _answers(detail: dict) -> list[dict]:
    """A fixed, varied answer pattern that uses every response option."""
    values = [o["value"] for o in detail["response_options"]]
    return [
        {"item_id": item["id"], "value": values[(n * 3 + n // 4) % len(values)]}
        for n, item in enumerate(detail["items"])
    ]


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_fixed_answers_give_the_stored_result(client, instrument):
    detail = client.get(f"/api/v1/assessments/{instrument}").json()
    sid, h, _ = start(client, instrument)
    r = client.put(
        f"/api/v1/assessment-sessions/{sid}/answers", json={"answers": _answers(detail)}, headers=h
    )
    assert r.status_code == 200, r.text
    done = client.post(f"/api/v1/assessment-sessions/{sid}/complete", headers=h)
    assert done.status_code == 200, done.text
    result = client.get(f"/api/v1/results/{done.json()['id']}", headers=h)
    assert result.status_code == 200, result.text
    actual = _scrub(result.json())

    path = GOLDEN / f"{instrument}.json"
    if os.environ.get("PDNA_UPDATE_GOLDEN") == "1":
        GOLDEN.mkdir(exist_ok=True)
        path.write_text(json.dumps(actual, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    assert path.exists(), f"No snapshot for {instrument}; run with PDNA_UPDATE_GOLDEN=1 and review it"
    assert actual == json.loads(path.read_text()), f"{instrument} result changed; see the module docstring"
