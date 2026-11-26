import itertools

from app.personality.archetypes import match_archetypes

TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "emotional_stability"]


def _scores(**kw):
    base = dict.fromkeys(TRAITS, 50.0)
    base.update(kw)
    return base


def test_each_archetype_is_reachable_from_its_own_prototype(content):
    arch = content.archetypes.data
    for a in arch.archetypes:
        scores = _scores(**{t: (90.0 if s > 0 else 10.0) for t, s in a.prototype.items()})
        assert match_archetypes(arch, scores).primary.id == a.id, a.id


def test_balanced_profile_is_flagged_weak(content):
    m = match_archetypes(content.archetypes.data, _scores())
    assert m.weak_fit
    assert m.primary.fit == 0.0


def test_primary_and_secondary_differ_and_are_deterministic(content):
    arch = content.archetypes.data
    for vals in itertools.product([10.0, 50.0, 90.0], repeat=5):
        scores = dict(zip(TRAITS, vals, strict=True))
        m1 = match_archetypes(arch, scores)
        m2 = match_archetypes(arch, dict(reversed(list(scores.items()))))
        assert m1 == m2
        assert m1.primary.id != m2.secondary.id


def test_drivers_explain_fit(content):
    m = match_archetypes(content.archetypes.data, _scores(extraversion=90.0, agreeableness=80.0))
    assert m.primary.id == "connector"
    assert [t for t, _ in m.primary.drivers] == ["extraversion", "agreeableness"]
