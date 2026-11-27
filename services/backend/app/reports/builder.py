"""Builds a personality report from a person's latest results. Pure and deterministic: the same results and
the same content files always give the same report, so a stored report can be checked by rebuilding it.
Any change to what this function produces bumps REPORT_VERSION."""

import hashlib
import json

from app.api.schemas import ResultOut
from app.assessments.content import ContentBundle
from app.reports.schemas import (
    MethodologyItem,
    PlanItem,
    ReportArchetype,
    ReportBody,
    ReportInterestArea,
    ReportInterests,
    ReportLeadership,
    ReportSource,
    ReportTrait,
)

REPORT_VERSION = "1.0.0"
MAX_STRENGTHS = 8
MAX_DEVELOPMENT = 6
MAX_PLAN = 6


def _dedupe(items: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for i in items:
        if i not in out:
            out.append(i)
    return out[:limit]


def content_fingerprint(bundle: ContentBundle) -> str:
    """One hash over every content file a report draws on."""
    parts = [
        bundle.report.sha256,
        bundle.growth.sha256,
        bundle.leadership.sha256,
        bundle.interpretations.sha256,
        bundle.archetypes.sha256,
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def body_sha256(body: ReportBody) -> str:
    return hashlib.sha256(json.dumps(body.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


def build_report(bundle: ContentBundle, results: dict[str, ResultOut]) -> ReportBody:
    big_five = results.get("big_five")
    if big_five is None:
        raise ValueError("a report needs a Big Five result")
    interests = results.get("interests")
    leadership = results.get("leadership")
    rc = bundle.report.data
    growth = bundle.growth.data

    sources = [
        ReportSource(
            kind=kind,
            result_id=str(r.id),
            instrument_name=r.methodology.instrument_name,
            instrument_version=r.methodology.instrument_version,
            completed_at=r.created_at,
        )
        for kind, r in (("big_five", big_five), ("interests", interests), ("leadership", leadership))
        if r is not None
    ]

    arch = big_five.archetypes
    profile = (
        ReportArchetype(
            name=arch.primary.name,
            summary=arch.primary.summary,
            secondary=arch.secondary.name,
            weak_fit=arch.weak_fit,
            disclaimer=arch.disclaimer,
        )
        if arch
        else None
    )

    traits = []
    strengths: list[str] = list(arch.primary.strengths) if arch else []
    development: list[str] = list(arch.primary.growth) if arch else []
    programs: list[tuple[str, str]] = [(rc.default_program, rc.program_reasons[rc.default_program])]
    for t in big_five.traits:
        band = rc.traits.get(t.trait, {}).get(t.band) if t.band else None
        traits.append(
            ReportTrait(
                trait=t.trait,
                name=t.name,
                description=t.description,
                score=t.score,
                band=t.band,
                summary=t.summary,
                communication=band.communication if band else None,
                relationships=band.relationships if band else None,
            )
        )
        if t.band in ("lower", "higher"):
            strengths += t.strengths
            development += t.growth
        if band and band.program:
            programs.append((band.program, rc.program_reasons[band.program]))

    interests_out = None
    if interests and interests.interests:
        i = interests.interests
        top = [] if i.empty else i.areas[:3]
        interests_out = ReportInterests(
            code=None if i.empty else i.code,
            top=[ReportInterestArea(name=a.name, short=a.short, count=a.count, total=a.total) for a in top],
            fields=_dedupe([f for a in top for f in a.fields[:3]], 9),
            note=i.note,
        )
        if not i.empty:
            programs.append((rc.interest_program, rc.program_reasons[rc.interest_program]))

    leadership_out = None
    lead_plan: list[PlanItem] = []
    if leadership and leadership.leadership:
        lead = leadership.leadership
        names = {a.area: a.name for a in lead.areas}
        leadership_out = ReportLeadership(
            most_preferred=[names[a] for a in lead.top],
            least_preferred=[names[a] for a in lead.stretch],
            even=lead.even,
            note=lead.note,
        )
        lead_plan = [
            PlanItem(
                kind="leadership_module",
                id=m.id,
                title=m.title,
                reason="Builds on a leadership preference."
                if m.reason == "build"
                else "A stretch area to practise.",
                href=f"/leadership/{m.id}",
            )
            for m in lead.recommended_modules
        ]

    plan: list[PlanItem] = []
    for program_id, reason in programs:
        p = growth.program(program_id)
        if p is not None and all(x.id != p.id for x in plan):
            plan.append(
                PlanItem(kind="program", id=p.id, title=p.title, reason=reason, href=f"/growth/{p.id}")
            )
    plan = (plan + lead_plan)[:MAX_PLAN]

    methodology = [
        MethodologyItem(
            kind=s.kind,
            instrument_name=r.methodology.instrument_name,
            instrument_version=r.methodology.instrument_version,
            engine_version=r.methodology.engine_version,
            content_sha256=r.methodology.content_sha256,
            answers_sha256=r.methodology.answers_sha256,
            scoring_summary=r.methodology.scoring_summary,
            band_note=r.methodology.band_note,
            limitations=list(r.methodology.limitations),
            references=list(r.methodology.references),
            attribution=r.methodology.attribution,
        )
        for s, r in zip(sources, [x for x in (big_five, interests, leadership) if x is not None], strict=True)
    ]

    return ReportBody(
        report_version=REPORT_VERSION,
        content_sha256=content_fingerprint(bundle),
        sources=sources,
        note=rc.note,
        profile=profile,
        traits=traits,
        strengths=_dedupe(strengths, MAX_STRENGTHS),
        development=_dedupe(development, MAX_DEVELOPMENT),
        interests=interests_out,
        leadership=leadership_out,
        values_note=rc.values_note,
        plan=plan,
        methodology=methodology,
        limitations=list(rc.general_limitations),
    )
