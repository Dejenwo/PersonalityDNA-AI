"""Turn stored rows plus versioned content into API responses."""

from app.api.schemas import (
    ArchetypeOut,
    ArchetypesOut,
    AssessmentDetail,
    AssessmentItem,
    AssessmentSource,
    AssessmentSummary,
    Methodology,
    Progress,
    ResponseOption,
    ResultOut,
    SessionOut,
    TraitResult,
)
from app.assessments.content import ContentBundle, Instrument
from app.assessments.service import answers_of, instrument_for
from app.database.models import AssessmentResult, AssessmentSession

TRAIT_LABEL = {
    "openness": "openness",
    "conscientiousness": "conscientiousness",
    "extraversion": "extraversion",
    "agreeableness": "agreeableness",
    "emotional_stability": "emotional stability",
}

LIMITATIONS = [
    "Results describe how you rated yourself today. Self-ratings can shift with mood, context and time.",
    "Scores show where your answers fall on the 1-5 response scale. They are not percentiles and do not "
    "compare you with other people, because no reference population data is used.",
    "This is not a clinical or diagnostic tool and says nothing about mental health conditions.",
    "Archetypes are original descriptive summaries, not scientifically validated types. Most people show "
    "elements of several.",
    "Personality alone does not determine career success, relationship outcomes or suitability for any role. "
    "Do not use these results for hiring or other decisions about people.",
]


def summary(inst: Instrument) -> AssessmentSummary:
    return AssessmentSummary(
        id=inst.id,
        version=inst.version,
        name=inst.name,
        tier=inst.tier,
        item_count=len(inst.items),
        estimated_minutes=inst.estimated_minutes,
        locale=inst.locale,
    )


def detail(inst: Instrument) -> AssessmentDetail:
    return AssessmentDetail(
        **summary(inst).model_dump(),
        instructions=inst.instructions,
        response_options=[
            ResponseOption(value=lbl.value, label=lbl.label) for lbl in inst.response_scale.labels
        ],
        items=[AssessmentItem(id=i.id, number=i.number, text=i.text) for i in inst.items],
        source=AssessmentSource(**inst.source.model_dump()),
        references=list(inst.references),
        license=inst.license.id,
    )


def progress(answered: int, total: int) -> Progress:
    return Progress(
        answered=answered, total=total, percent=round(answered / total * 100, 1) if total else 0.0
    )


def session_out(bundle: ContentBundle, s: AssessmentSession) -> SessionOut:
    inst = instrument_for(bundle, s).data
    answers = answers_of(s)
    return SessionOut(
        id=s.id,
        instrument_id=inst.id,
        instrument_version=inst.version,
        status=s.status,
        started_at=s.started_at,
        completed_at=s.completed_at,
        answers=answers,
        progress=progress(len(answers), len(inst.items)),
        result_id=s.result.id if s.result else None,
    )


def result_out(bundle: ContentBundle, r: AssessmentResult) -> ResultOut:
    inst = bundle.instrument(r.instrument_id, r.instrument_version).data
    interp = bundle.interpretations.data
    arch_defs = {a.id: a for a in bundle.archetypes.data.archetypes}

    traits: list[TraitResult] = []
    for ts in r.trait_scores:
        text = interp.traits[ts.trait]
        band_text = text.bands[ts.band] if ts.band else None  # type: ignore[index]
        traits.append(
            TraitResult(
                trait=ts.trait,
                name=text.name,
                description=text.short,
                status=ts.status,
                score=ts.score,
                raw_mean=ts.raw_mean,
                band=ts.band,
                answered=ts.answered,
                total=ts.total,
                summary=band_text.summary if band_text else None,
                strengths=list(band_text.strengths) if band_text else [],
                growth=list(band_text.growth) if band_text else [],
            )
        )
    stability = next((t.score for t in traits if t.trait == "emotional_stability"), None)

    def arch(entry: dict) -> ArchetypeOut:  # type: ignore[type-arg]
        a = arch_defs[entry["id"]]
        drivers = [
            f"{'higher' if a.prototype[t] > 0 else 'lower'} {TRAIT_LABEL.get(t, t)}"
            for t, _ in entry["drivers"]
        ]
        return ArchetypeOut(
            id=a.id,
            name=a.name,
            fit=entry["fit"],
            summary=a.summary,
            strengths=list(a.strengths),
            growth=list(a.growth),
            drivers=drivers,
        )

    ranking = r.archetypes["ranking"]
    return ResultOut(
        id=r.id,
        session_id=r.session_id,
        created_at=r.created_at,
        traits=traits,
        negative_emotionality=round(100 - stability, 1) if stability is not None else None,
        archetypes=ArchetypesOut(
            version=r.archetype_version,
            disclaimer=bundle.archetypes.data.disclaimer,
            weak_fit=r.archetypes["weak_fit"],
            primary=arch(ranking[0]),
            secondary=arch(ranking[1]),
        ),
        quality_flags=r.quality_flags,
        methodology=Methodology(
            engine_version=r.engine_version,
            instrument_id=r.instrument_id,
            instrument_version=r.instrument_version,
            instrument_name=inst.source.name,
            content_sha256=r.content_sha256,
            answers_sha256=r.answers_sha256,
            scoring_summary=(
                "Each answer is scored 1-5. Negatively worded items are reversed (6 minus the answer). "
                "Each trait score is the average of its items, shown on a 0-100 scale where 0 means every "
                "answer was at the low end and 100 means every answer was at the high end."
            ),
            band_note="Lower is below 40, middle is 40-60, higher is above 60 on that 0-100 scale.",
            negative_emotionality_note=(
                "The instrument measures Emotional Stability. Negative Emotionality (often called "
                "Neuroticism) is the same scale in the reverse direction: 100 minus Emotional Stability."
            ),
            limitations=LIMITATIONS,
            references=list(inst.references),
            attribution="Items from the International Personality Item Pool (ipip.ori.org), public domain.",
        ),
    )
