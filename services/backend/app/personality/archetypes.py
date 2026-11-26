"""Deterministic mapping from Big Five scores to original, descriptive archetypes."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from app.assessments.content import ArchetypeSet


@dataclass(frozen=True)
class ArchetypeFit:
    id: str
    name: str
    fit: float
    # Traits that pushed this archetype up, strongest first: (trait, contribution).
    drivers: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class ArchetypeMatch:
    version: str
    primary: ArchetypeFit
    secondary: ArchetypeFit
    weak_fit: bool
    ranking: tuple[ArchetypeFit, ...]


def match_archetypes(archetypes: ArchetypeSet, scores: Mapping[str, float]) -> ArchetypeMatch:
    missing = [t for t in archetypes.traits if t not in scores]
    if missing:
        raise ValueError(f"missing trait scores: {missing}")
    centred = {t: (scores[t] - 50.0) / 50.0 for t in archetypes.traits}

    fits: list[tuple[float, int, ArchetypeFit]] = []
    for order, a in enumerate(archetypes.archetypes):
        contributions = {t: sign * centred[t] for t, sign in a.prototype.items()}
        fit = round(sum(contributions.values()) / math.sqrt(len(a.prototype)), 6)
        drivers = tuple(
            sorted(((t, round(c, 4)) for t, c in contributions.items() if c > 0), key=lambda x: (-x[1], x[0]))
        )
        fits.append((fit, order, ArchetypeFit(a.id, a.name, fit, drivers)))

    fits.sort(key=lambda x: (-x[0], x[1]))
    ranking = tuple(f for _, _, f in fits)
    return ArchetypeMatch(
        version=archetypes.version,
        primary=ranking[0],
        secondary=ranking[1],
        weak_fit=ranking[0].fit < archetypes.weak_fit_threshold,
        ranking=ranking,
    )
