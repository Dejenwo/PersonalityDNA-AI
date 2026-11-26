"""Interest profile from scored RIASEC areas. Pure and deterministic, like the scoring engine."""

from dataclasses import dataclass

# Holland's order. Used only to make tie ordering deterministic; ties are reported, never hidden.
RIASEC = ("realistic", "investigative", "artistic", "social", "enterprising", "conventional")
LETTER = {area: area[0].upper() for area in RIASEC}


@dataclass(frozen=True)
class InterestProfile:
    ranking: tuple[tuple[str, int], ...]  # (area, count), highest first
    code: str  # top three letters, e.g. "IAS"
    # Areas tied with another area that straddles the top-three boundary, so the code could differ.
    boundary_ties: tuple[str, ...]
    # True when nothing was endorsed, so there is no meaningful code.
    empty: bool


def interest_profile(counts: dict[str, int]) -> InterestProfile:
    unknown = set(counts) - set(RIASEC)
    if unknown or set(counts) != set(RIASEC):
        raise ValueError(f"expected counts for exactly {RIASEC}, got {sorted(counts)}")
    ranking = tuple(sorted(counts.items(), key=lambda kv: (-kv[1], RIASEC.index(kv[0]))))
    third = ranking[2][1]
    inside = [a for a, c in ranking[:3] if c == third]
    outside = [a for a, c in ranking[3:] if c == third]
    ties = tuple(inside + outside) if outside else ()
    return InterestProfile(
        ranking=ranking,
        code="".join(LETTER[a] for a, _ in ranking[:3]),
        boundary_ties=ties,
        empty=all(c == 0 for c in counts.values()),
    )
