import pytest

from app.scoring.engine import ScoringError, band_for, score


def _all(inst, value):
    return {i.id: value for i in inst.items}


def test_all_neutral_scores_fifty(content):
    inst = content.instrument("ipip-bfm-50", "1.0.0").data
    out = score(inst, _all(inst, 3))
    assert out.complete
    assert {s.score for s in out.scales} == {50.0}


def test_reverse_scoring_hand_computed(content):
    """All answers 5: plus-keyed items score 5, minus-keyed score 1.

    Extraversion: 5 plus, 5 minus -> mean 3.0 -> 50.0
    Agreeableness: 6 plus, 4 minus -> (30+4)/10 = 3.4 -> 60.0
    Conscientiousness: 6 plus, 4 minus -> 3.4 -> 60.0
    Emotional stability: 2 plus, 8 minus -> (10+8)/10 = 1.8 -> 20.0
    Openness: 7 plus, 3 minus -> (35+3)/10 = 3.8 -> 70.0
    """
    inst = content.instrument("ipip-bfm-50", "1.0.0").data
    out = score(inst, _all(inst, 5))
    got = {s.scale_id: (s.raw_mean, s.score, s.band) for s in out.scales}
    assert got == {
        "extraversion": (3.0, 50.0, "middle"),
        "agreeableness": (3.4, 60.0, "middle"),
        "conscientiousness": (3.4, 60.0, "middle"),
        "emotional_stability": (1.8, 20.0, "lower"),
        "openness": (3.8, 70.0, "higher"),
    }
    assert out.quality_flags == ("uniform_responses",)


def test_keyed_extremes_give_0_and_100(content):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    high = {i.id: (5 if i.keyed == "+" else 1) for i in inst.items}
    low = {i.id: (1 if i.keyed == "+" else 5) for i in inst.items}
    assert {s.score for s in score(inst, high).scales} == {100.0}
    assert {s.score for s in score(inst, low).scales} == {0.0}


def test_rounding_is_half_up_and_deterministic(content):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    # Extraversion items: 01(+), 06(-), 11(+), 16(-). Answers 4,2,4,3 -> 4,4,4,3 -> mean 3.75 -> 68.75 -> 68.8
    answers = _all(inst, 3)
    answers.update({"mini20-01": 4, "mini20-06": 2, "mini20-11": 4, "mini20-16": 3})
    first = score(inst, answers)
    assert first.score_of("extraversion") == 68.8
    for _ in range(50):
        again = score(inst, dict(reversed(list(answers.items()))))
        assert again == first


def test_missing_answers_prorated_until_threshold(content):
    inst = content.instrument("ipip-bfm-50", "1.0.0").data
    answers = _all(inst, 3)
    # Remove two extraversion items: 8 of 10 answered is allowed.
    del answers["bfm50-01"], answers["bfm50-06"]
    out = score(inst, answers)
    ext = next(s for s in out.scales if s.scale_id == "extraversion")
    assert (ext.status, ext.answered, ext.total, ext.score) == ("scored", 8, 10, 50.0)
    # A third missing item makes the scale insufficient.
    del answers["bfm50-11"]
    out = score(inst, answers)
    ext = next(s for s in out.scales if s.scale_id == "extraversion")
    assert ext.status == "insufficient" and ext.score is None
    assert not out.complete


def test_mini_requires_all_items(content):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    answers = _all(inst, 2)
    del answers["mini20-20"]
    assert not score(inst, answers).complete


@pytest.mark.parametrize(
    "answers,match",
    [
        ({"nope": 3}, "unknown item"),
        ({"mini20-01": 6}, "between"),
        ({"mini20-01": 0}, "between"),
        ({"mini20-01": "3"}, "integer"),
        ({"mini20-01": True}, "integer"),
    ],
)
def test_invalid_answers_rejected(content, answers, match):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    with pytest.raises(ScoringError, match=match):
        score(inst, answers)


def test_digest_depends_on_answers_not_order(content):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    a = _all(inst, 3)
    b = dict(reversed(list(a.items())))
    assert score(inst, a).answers_sha256 == score(inst, b).answers_sha256
    b["mini20-01"] = 4
    assert score(inst, a).answers_sha256 != score(inst, b).answers_sha256


def test_rapid_completion_flag(content):
    inst = content.instrument("mini-ipip-20", "1.0.0").data
    varied = {i.id: (i.number % 5) + 1 for i in inst.items}
    assert score(inst, varied, elapsed_seconds=10).quality_flags == ("rapid_completion",)
    assert score(inst, varied, elapsed_seconds=120).quality_flags == ()


@pytest.mark.parametrize(
    "value,band",
    [(0, "lower"), (39.9, "lower"), (40, "middle"), (60, "middle"), (60.1, "higher"), (100, "higher")],
)
def test_band_boundaries(value, band):
    from decimal import Decimal

    assert band_for(Decimal(str(value))) == band
