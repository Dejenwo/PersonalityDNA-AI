"""Deterministic scoring engine.

Pure functions only: no I/O, no clock, no randomness, no AI. The same answers to the same
instrument version always produce the same output. Change ENGINE_VERSION whenever the
arithmetic or rules change, so stored results remain auditable.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.assessments.content import Instrument

# 1.1.0 added count_endorsed scoring for interest checklists. Likert arithmetic is unchanged since 1.0.0.
ENGINE_VERSION = "1.1.0"

Band = Literal["lower", "middle", "higher"]
BAND_LOWER_BELOW = Decimal(40)
BAND_HIGHER_ABOVE = Decimal(60)
UNIFORM_MIN_ANSWERS = 10
RAPID_SECONDS_PER_ITEM = 1.5


class ScoringError(ValueError):
    """Answers are invalid for this instrument."""


@dataclass(frozen=True)
class ScaleScore:
    scale_id: str
    status: Literal["scored", "insufficient"]
    answered: int
    total: int
    # likert_mean: mean item value after reverse keying. count_endorsed: number of activities endorsed.
    raw_mean: float | None
    score: float | None  # 0..100
    band: Band | None


@dataclass(frozen=True)
class ScoringOutput:
    engine_version: str
    instrument_id: str
    instrument_version: str
    answers_sha256: str
    scales: tuple[ScaleScore, ...]
    quality_flags: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return all(s.status == "scored" for s in self.scales)

    def score_of(self, scale_id: str) -> float | None:
        for s in self.scales:
            if s.scale_id == scale_id:
                return s.score
        raise KeyError(scale_id)


def _round1(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def band_for(score: Decimal) -> Band:
    if score < BAND_LOWER_BELOW:
        return "lower"
    if score > BAND_HIGHER_ABOVE:
        return "higher"
    return "middle"


def validate_answers(instrument: Instrument, answers: Mapping[str, int]) -> None:
    rs = instrument.response_scale
    for item_id, value in answers.items():
        if item_id not in instrument.items_by_id:
            raise ScoringError(f"unknown item {item_id!r}")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ScoringError(f"answer for {item_id!r} must be an integer")
        if not rs.min <= value <= rs.max:
            raise ScoringError(f"answer for {item_id!r} must be between {rs.min} and {rs.max}")


def answers_digest(instrument: Instrument, answers: Mapping[str, int]) -> str:
    canonical = json.dumps(
        {
            "instrument": instrument.id,
            "version": instrument.version,
            "answers": dict(sorted(answers.items())),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def score(
    instrument: Instrument,
    answers: Mapping[str, int],
    *,
    elapsed_seconds: float | None = None,
) -> ScoringOutput:
    validate_answers(instrument, answers)
    rs = instrument.response_scale
    reverse_base = rs.min + rs.max
    span = Decimal(rs.max - rs.min)

    scales: list[ScaleScore] = []
    for scale in instrument.scales:
        items = [i for i in instrument.items if i.scale == scale.id]
        values = [
            (reverse_base - answers[i.id]) if i.keyed == "-" else answers[i.id]
            for i in items
            if i.id in answers
        ]
        if len(values) < scale.min_items_answered:
            scales.append(ScaleScore(scale.id, "insufficient", len(values), len(items), None, None, None))
            continue
        if instrument.scoring == "count_endorsed":
            # Published checklist scoring: one point per activity the person would like to do.
            # Displayed on 0-100 as count / items; no bands, because interest levels have no norms here.
            count = sum(1 for v in values if v == rs.max)
            scales.append(
                ScaleScore(
                    scale_id=scale.id,
                    status="scored",
                    answered=len(values),
                    total=len(items),
                    raw_mean=float(count),
                    score=float(_round1(Decimal(count) / Decimal(len(items)) * 100)),
                    band=None,
                )
            )
            continue
        mean = Decimal(sum(values)) / Decimal(len(values))
        normalized = _round1((mean - rs.min) / span * 100)
        scales.append(
            ScaleScore(
                scale_id=scale.id,
                status="scored",
                answered=len(values),
                total=len(items),
                raw_mean=float(mean.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                score=float(normalized),
                band=band_for(normalized),
            )
        )

    flags: list[str] = []
    if len(answers) >= UNIFORM_MIN_ANSWERS and len(set(answers.values())) == 1:
        flags.append("uniform_responses")
    if elapsed_seconds is not None and answers and elapsed_seconds < RAPID_SECONDS_PER_ITEM * len(answers):
        flags.append("rapid_completion")

    return ScoringOutput(
        engine_version=ENGINE_VERSION,
        instrument_id=instrument.id,
        instrument_version=instrument.version,
        answers_sha256=answers_digest(instrument, answers),
        scales=tuple(scales),
        quality_flags=tuple(flags),
    )
