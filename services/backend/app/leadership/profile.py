"""Ranks leadership preference areas and picks development modules. Pure and deterministic.

Scores come from the scoring engine (0-100 position on the response scale). They are preferences,
compared only with each other: no bands, norms or percentiles.
"""

from dataclasses import dataclass

# When the highest and lowest areas are this close, the profile is described as fairly even.
EVEN_RANGE = 10.0


@dataclass(frozen=True)
class LeadershipProfile:
    ranking: tuple[tuple[str, float], ...]
    top: tuple[str, ...]
    stretch: tuple[str, ...]
    even: bool

    @property
    def recommended(self) -> tuple[tuple[str, str], ...]:
        """(area, reason): build on the strongest preference, then stretch the two least preferred."""
        if not self.ranking:
            return ()
        return ((self.top[0], "build"), *((a, "stretch") for a in self.stretch))


def leadership_profile(scores: dict[str, float | None], order: list[str]) -> LeadershipProfile:
    """`order` is the content order, used to break ties so the result never depends on dict order."""
    unknown = set(scores) - set(order)
    if unknown:
        raise ValueError(f"unknown areas: {sorted(unknown)}")
    scored = [(a, s) for a in order if (s := scores.get(a)) is not None]
    ranking = tuple(sorted(scored, key=lambda x: (-x[1], order.index(x[0]))))
    if not ranking:
        return LeadershipProfile((), (), (), False)
    top = tuple(a for a, _ in ranking[:3])
    stretch = tuple(a for a, _ in ranking[-2:] if a not in top) if len(ranking) > 3 else ()
    even = ranking[0][1] - ranking[-1][1] < EVEN_RANGE
    return LeadershipProfile(ranking, top, stretch, even)
