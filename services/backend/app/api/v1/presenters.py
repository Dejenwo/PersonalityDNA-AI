"""Turn stored rows plus versioned content into API responses."""

from app.api.schemas import (
    ArchetypeOut,
    ArchetypesOut,
    AssessmentDetail,
    AssessmentItem,
    AssessmentSource,
    AssessmentSummary,
    ExploreLinkOut,
    InterestAreaOut,
    InterestsOut,
    LeadershipAreaOut,
    LeadershipOut,
    Methodology,
    ModuleSummaryOut,
    Progress,
    ResponseOption,
    ResultOut,
    SessionOut,
    TraitResult,
)
from app.assessments.content import ContentBundle, Instrument, LeadershipModule
from app.assessments.service import answers_of, instrument_for
from app.careers.interests import LETTER
from app.database.models import AssessmentResult, AssessmentSession
from app.leadership.profile import leadership_profile

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
        family=inst.family,
        status=inst.status,
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


INTEREST_LIMITATIONS = [
    "Results show which work activities you said you would like to do today. Interests can change over time.",
    "Interests are not abilities. They say nothing about how well you would do any job, and they are not "
    "a recommendation to take or avoid any career.",
    "Area scores count your choices. They are not percentiles and do not compare you with other people.",
    "Do not use these results for hiring or other decisions about people.",
]

ONET_ATTRIBUTION = (
    "This assessment uses the O*NET\u00ae Interest Profiler Short Form from the O*NET Career "
    "Exploration Tools by the U.S. Department of Labor, Employment and Training Administration "
    "(USDOL/ETA), used under the "
    "CC BY-ND 4.0 licence. O*NET\u00ae is a trademark of USDOL/ETA. PersonalityDNA is not affiliated with or "
    "endorsed by USDOL/ETA."
)


def interests_result_out(bundle: ContentBundle, r: AssessmentResult) -> ResultOut:
    inst = bundle.instrument(r.instrument_id, r.instrument_version).data
    interp = bundle.interests.data
    profile = r.interest_profile or {}
    totals = {ts.trait: ts for ts in r.trait_scores}
    areas = []
    for area, count in profile.get("ranking", []):
        text = interp.areas[area]
        ts = totals[area]
        areas.append(
            InterestAreaOut(
                area=area,
                letter=LETTER[area],
                name=text.name,
                short=text.short,
                count=count,
                total=ts.total,
                score=ts.score or 0.0,
                enjoys=list(text.enjoys),
                fields=list(text.fields),
                reflection=text.reflection,
            )
        )
    return ResultOut(
        id=r.id,
        session_id=r.session_id,
        created_at=r.created_at,
        kind="interests",
        traits=[],
        negative_emotionality=None,
        archetypes=None,
        interests=InterestsOut(
            code=profile.get("code", ""),
            empty=bool(profile.get("empty")),
            boundary_ties=[interp.areas[a].name for a in profile.get("boundary_ties", [])],
            areas=areas,
            note=interp.note,
            explore_links=[ExploreLinkOut(label=lk.label, url=lk.url) for lk in interp.explore_links],
            draft=inst.status == "draft",
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
                "Each interest area has 10 work activities. Its score is the number of activities you said "
                "you would like to do (0 to 10), as on the published self-scoring form. "
                "Your interest code is the first letters of your three highest areas."
            ),
            band_note="Interest areas are ranked against each other, not placed in bands.",
            negative_emotionality_note=None,
            limitations=INTEREST_LIMITATIONS,
            references=list(inst.references),
            attribution=ONET_ATTRIBUTION,
        ),
    )


LEADERSHIP_LIMITATIONS = [
    "This is an original reflection questionnaire. It has not been scientifically validated "
    "and has no norms.",
    "Scores show which leadership activities you enjoy most and least today, compared only with each other. "
    "They are not abilities and they change with experience.",
    "Leadership preferences must never be used to hire, promote, rate or select anyone.",
]


def leadership_out(bundle: ContentBundle, r: AssessmentResult) -> LeadershipOut:
    program = bundle.leadership.data
    order = list(program.areas)
    names = {s.id: s.name for s in bundle.instrument(r.instrument_id, r.instrument_version).data.scales}
    profile = leadership_profile({ts.trait: ts.score for ts in r.trait_scores}, order)
    areas = [
        LeadershipAreaOut(
            area=a,
            name=names[a],
            short=program.areas[a].short,
            score=score,
            text=program.areas[a].stretch if a in profile.stretch else program.areas[a].preferred,
        )
        for a, score in profile.ranking
    ]
    modules = []
    for area, reason in profile.recommended:
        m = program.module(program.areas[area].module)
        if m is not None:
            modules.append(module_summary(m, reason))
    return LeadershipOut(
        areas=areas,
        top=list(profile.top),
        stretch=list(profile.stretch),
        even=profile.even,
        recommended_modules=modules,
        note=program.note,
    )


def module_summary(m: LeadershipModule, reason: str | None = None) -> ModuleSummaryOut:
    return ModuleSummaryOut(id=m.id, area=m.area, title=m.title, summary=m.summary, reason=reason)


def leadership_result_out(bundle: ContentBundle, r: AssessmentResult) -> ResultOut:
    inst = bundle.instrument(r.instrument_id, r.instrument_version).data
    return ResultOut(
        id=r.id,
        session_id=r.session_id,
        created_at=r.created_at,
        kind="leadership",
        traits=[],
        negative_emotionality=None,
        archetypes=None,
        interests=None,
        leadership=leadership_out(bundle, r),
        quality_flags=r.quality_flags,
        methodology=Methodology(
            engine_version=r.engine_version,
            instrument_id=r.instrument_id,
            instrument_version=r.instrument_version,
            instrument_name=inst.source.name,
            content_sha256=r.content_sha256,
            answers_sha256=r.answers_sha256,
            scoring_summary=(
                "Each answer is scored 1 to 5. Each area's score is the average of its three statements, "
                "shown on a 0-100 scale where 0 means every answer was 'Not at all' and 100 means every "
                "answer was 'Very much'. Areas are ranked against each other; ties keep a fixed order."
            ),
            band_note="Leadership areas are ranked against each other, not placed in bands.",
            negative_emotionality_note=None,
            limitations=LEADERSHIP_LIMITATIONS,
            references=list(inst.references),
            attribution="Original PersonalityDNA content.",
        ),
    )


def result_out(bundle: ContentBundle, r: AssessmentResult) -> ResultOut:
    inst = bundle.instrument(r.instrument_id, r.instrument_version).data
    if inst.family == "interests":
        return interests_result_out(bundle, r)
    if inst.family == "leadership":
        return leadership_result_out(bundle, r)
    assert r.archetypes is not None and r.archetype_version is not None
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
        kind="big_five",
        traits=traits,
        negative_emotionality=round(100 - stability, 1) if stability is not None else None,
        archetypes=ArchetypesOut(
            version=r.archetype_version,
            disclaimer=bundle.archetypes.data.disclaimer,
            weak_fit=r.archetypes["weak_fit"],
            primary=arch(ranking[0]),
            secondary=arch(ranking[1]),
        ),
        interests=None,
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
