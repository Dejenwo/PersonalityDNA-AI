"""Builds the coach's context from data the user authorized. Scores only: never raw answers or identity."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.assessments.content import ContentBundle
from app.database.models import AssessmentResult

TOPICS: dict[str, tuple[str, str]] = {
    "results": (
        "Understanding my results",
        "Help the user understand what their results describe and how these tendencies can show up "
        "in everyday life.",
    ),
    "communication": (
        "Communication",
        "Help the user notice their communication habits and practise small adjustments.",
    ),
    "relationships": (
        "Relationships",
        "Focus on the user's own communication, needs and reflection. Do not assess, label or diagnose "
        "the other people they mention, and never predict how a relationship will turn out.",
    ),
    "career": (
        "Career exploration",
        "Help the user explore interests, working preferences and learning opportunities. Never say "
        "which job they are suited for or predict their performance.",
    ),
    "leadership": (
        "Leadership",
        "Help the user reflect on how they lead, delegate, give feedback and support others.",
    ),
    "goals": (
        "Goals and habits",
        "Help the user set one small, specific goal and a habit that fits their tendencies.",
    ),
    "general": (
        "Something else",
        "Coach on whatever everyday personal-development question the user brings, within your rules.",
    ),
}


def fmt_score(value: float) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class TraitFact:
    trait: str
    name: str
    score: float | None
    band: str | None
    growth: tuple[str, ...] = ()

    @property
    def score_text(self) -> str:
        return fmt_score(self.score) if self.score is not None else "not scored"


@dataclass(frozen=True)
class CoachFacts:
    topic: str = "general"
    instrument_name: str | None = None
    completed_on: str | None = None
    traits: tuple[TraitFact, ...] = ()
    negative_emotionality: float | None = None
    archetype_name: str | None = None
    archetype_fit: float | None = None
    quality_flags: tuple[str, ...] = ()
    crisis_support_shown: bool = False
    notes: tuple[str, ...] = field(default=())
    # Career interests (RIASEC): code and (area name, count, total) highest first.
    interest_code: str | None = None
    interest_areas: tuple[tuple[str, int, int], ...] = ()
    interest_ties: tuple[str, ...] = ()

    @property
    def has_results(self) -> bool:
        return any(t.score is not None for t in self.traits)

    def scores(self) -> dict[str, float]:
        """Trait display name (lower case) -> score, including the derived Negative Emotionality."""
        out = {t.name.lower(): t.score for t in self.traits if t.score is not None}
        if self.negative_emotionality is not None:
            out["negative emotionality"] = self.negative_emotionality
        return out


_QUALITY_TEXT = {
    "uniform_responses": "Many answers were identical, so these results may describe the user less well.",
    "rapid_completion": "The statements were answered very quickly, so hold these results loosely.",
}


def _interest_facts(bundle: ContentBundle, result: AssessmentResult | None) -> dict[str, object]:
    profile = result.interest_profile if result is not None else None
    if not profile or profile.get("empty"):
        return {}
    areas = bundle.interests.data.areas
    totals = {ts.trait: ts.total for ts in result.trait_scores} if result is not None else {}
    return {
        "interest_code": profile["code"],
        "interest_areas": tuple((areas[a].name, int(c), totals.get(a, 10)) for a, c in profile["ranking"]),
        "interest_ties": tuple(areas[a].name for a in profile.get("boundary_ties", [])),
    }


def facts_from_result(
    bundle: ContentBundle,
    result: AssessmentResult | None,
    topic: str,
    *,
    crisis_support_shown: bool,
    interests: AssessmentResult | None = None,
) -> CoachFacts:
    extra = _interest_facts(bundle, interests)
    if result is None or result.archetypes is None:
        return CoachFacts(topic=topic, crisis_support_shown=crisis_support_shown, **extra)  # type: ignore[arg-type]
    inst = bundle.instrument(result.instrument_id, result.instrument_version).data
    interp = bundle.interpretations.data
    traits = []
    for ts in result.trait_scores:
        text = interp.traits[ts.trait]
        band_text = text.bands[ts.band] if ts.band in ("lower", "middle", "higher") else None  # type: ignore[index]
        traits.append(
            TraitFact(
                trait=ts.trait,
                name=text.name,
                score=ts.score,
                band=ts.band,
                growth=tuple(band_text.growth) if band_text else (),
            )
        )
    stability = next((t.score for t in traits if t.trait == "emotional_stability"), None)
    archetype_name = archetype_fit = None
    if not result.archetypes.get("weak_fit"):
        top = result.archetypes["ranking"][0]
        names = {a.id: a.name for a in bundle.archetypes.data.archetypes}
        archetype_name, archetype_fit = names.get(top["id"]), float(top["fit"])
    return CoachFacts(
        topic=topic,
        instrument_name=inst.name,
        completed_on=result.created_at.date().isoformat(),
        traits=tuple(traits),
        negative_emotionality=round(100 - stability, 1) if stability is not None else None,
        archetype_name=archetype_name,
        archetype_fit=archetype_fit,
        quality_flags=tuple(result.quality_flags),
        crisis_support_shown=crisis_support_shown,
        **extra,  # type: ignore[arg-type]
    )


def render_context(facts: CoachFacts) -> str:
    label, focus = TOPICS.get(facts.topic, TOPICS["general"])
    lines = ["## Context for this conversation", "", f"Conversation focus: {label}. {focus}", ""]
    if not facts.has_results:
        lines.append("Assessment results: the user has not shared any assessment results with you.")
    else:
        lines.append(f"Assessment: {facts.instrument_name}, completed {facts.completed_on}.")
        lines.append(
            "Trait scores on a 0 to 100 scale, calculated from the user's own answers. "
            "Bands: lower is below 40, middle is 40 to 60, higher is above 60. These are not percentiles."
        )
        for t in facts.traits:
            if t.score is None:
                lines.append(f"- {t.name}: not scored (too few statements were answered)")
            else:
                lines.append(f"- {t.name}: {t.score_text} ({t.band} band)")
        if facts.negative_emotionality is not None:
            lines.append(
                f"The app also shows Emotional Stability inverted as Negative Emotionality "
                f"{fmt_score(facts.negative_emotionality)}."
            )
        if facts.archetype_name:
            lines.append(
                f"Closest PersonalityDNA archetype: {facts.archetype_name} (fit {facts.archetype_fit}). "
                "Archetypes are original descriptive summaries of score patterns, not personality types."
            )
        else:
            lines.append("Archetype: none shown, because no archetype fits these scores clearly.")
        notes = [_QUALITY_TEXT[f] for f in facts.quality_flags if f in _QUALITY_TEXT]
        lines.append("Quality notes: " + (" ".join(notes) if notes else "none."))
    if facts.interest_code:
        areas = "; ".join(f"{n} {c} of {t}" for n, c, t in facts.interest_areas)
        lines.append(
            f"Career interests (O*NET Interest Profiler Short Form, activities the user would like to do): "
            f"code {facts.interest_code}; {areas}."
            + (f" Tied at third place: {', '.join(facts.interest_ties)}." if facts.interest_ties else "")
            + " Interests are preferences, not abilities, and never mean a job is or isn't suitable."
        )
    lines.append("User-stated goals: none recorded yet.")
    if facts.crisis_support_shown:
        lines.append(
            "Earlier in this conversation the app showed the user crisis support resources. "
            "Be attentive to their wellbeing and repeat those resources if distress comes up again."
        )
    return "\n".join(lines)
