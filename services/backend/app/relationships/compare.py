"""Deterministic comparison of two people's Big Five bands. Pure: no database, no AI.

Only bands (lower, middle, higher) are compared, never raw answers, and the output contains no
score, percentage or prediction about the relationship.
"""

from dataclasses import dataclass
from typing import Literal

from app.assessments.content import RelationshipInsights

Band = Literal["lower", "middle", "higher"]
Pattern = Literal["similar", "some_difference", "different"]


@dataclass(frozen=True)
class TraitComparison:
    trait: str
    name: str
    you: Band
    them: Band
    pattern: Pattern
    summary: str
    note: str
    misunderstanding: str | None
    prompt: str


def pattern_for(a: Band, b: Band) -> Pattern:
    if a == b:
        return "similar"
    if "middle" in (a, b):
        return "some_difference"
    return "different"


def compare(
    content: RelationshipInsights,
    names: dict[str, str],
    you: dict[str, Band | None],
    them: dict[str, Band | None],
) -> list[TraitComparison]:
    """One entry per trait both people have a band for, in content order; differences carry the
    complement, likely misunderstanding and a discussion prompt."""
    out: list[TraitComparison] = []
    for trait, text in content.traits.items():
        a, b = you.get(trait), them.get(trait)
        if a is None or b is None:
            continue
        pattern = pattern_for(a, b)
        if pattern == "similar":
            summary = (
                "You both sit in the middle here." if a == "middle" else f"You both tend to {text.poles[a]}."
            )
            out.append(
                TraitComparison(
                    trait, names[trait], a, b, pattern, summary, text.shared[a], None, text.prompt
                )
            )
            continue
        if pattern == "different":
            yours, theirs = text.poles[a], text.poles[b]  # type: ignore[index]
            summary = f"You tend to {yours}, while they tend to {theirs}."
        else:
            leaning = b if a == "middle" else a
            who = "They" if a == "middle" else "You"
            other = "you are" if a == "middle" else "they are"
            summary = f"{who} tend to {text.poles[leaning]}, while {other} in the middle."  # type: ignore[index]
        out.append(
            TraitComparison(
                trait,
                names[trait],
                a,
                b,
                pattern,
                summary,
                text.complement,
                text.misunderstanding,
                text.prompt,
            )
        )
    return out
