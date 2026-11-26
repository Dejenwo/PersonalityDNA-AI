from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorBody(Model):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(Model):
    error: ErrorBody


class ResponseOption(Model):
    value: int
    label: str


class AssessmentSummary(Model):
    id: str
    version: str
    name: str
    tier: Literal["quick", "comprehensive", "advanced"]
    family: Literal["big_five", "interests"]
    status: Literal["released", "draft"] = Field(description="Draft content is only served in development.")
    item_count: int
    estimated_minutes: int
    locale: str


class AssessmentItem(Model):
    id: str
    number: int
    text: str


class AssessmentSource(Model):
    name: str
    url: str
    authors: str


class AssessmentDetail(AssessmentSummary):
    instructions: str
    response_options: list[ResponseOption]
    items: list[AssessmentItem]
    source: AssessmentSource
    references: list[str]
    license: str


class AssessmentList(Model):
    items: list[AssessmentSummary]


class ConsentIn(Model):
    accepted: bool
    age_confirmed_18_plus: bool
    policy_version: str = Field(max_length=32)


class CreateSessionIn(Model):
    instrument_id: str = Field(max_length=64)
    version: str | None = Field(default=None, max_length=32)
    locale: str = Field(default="en", max_length=16)
    consent: ConsentIn


class Progress(Model):
    answered: int
    total: int
    percent: float


class SessionOut(Model):
    id: UUID
    instrument_id: str
    instrument_version: str
    status: Literal["in_progress", "completed", "abandoned"]
    started_at: datetime
    completed_at: datetime | None
    answers: dict[str, int]
    progress: Progress
    result_id: UUID | None


class CreateSessionOut(Model):
    session: SessionOut
    resume_token: str = Field(description="Shown once. Send as X-Session-Token on later requests.")


class AnswerIn(Model):
    item_id: str = Field(max_length=64)
    value: int | None = Field(description="Response value; null clears the answer.")


class SaveAnswersIn(Model):
    answers: list[AnswerIn] = Field(min_length=1, max_length=500)


class SaveAnswersOut(Model):
    saved: int
    progress: Progress


class TraitResult(Model):
    trait: str
    name: str
    description: str
    status: Literal["scored", "insufficient"]
    score: float | None = Field(description="0-100 position on the response scale; not a percentile.")
    raw_mean: float | None
    band: Literal["lower", "middle", "higher"] | None
    answered: int
    total: int
    summary: str | None
    strengths: list[str]
    growth: list[str]


class ArchetypeOut(Model):
    id: str
    name: str
    fit: float
    summary: str
    strengths: list[str]
    growth: list[str]
    drivers: list[str]


class ArchetypesOut(Model):
    version: str
    disclaimer: str
    weak_fit: bool
    primary: ArchetypeOut
    secondary: ArchetypeOut


class Methodology(Model):
    engine_version: str
    instrument_id: str
    instrument_version: str
    instrument_name: str
    content_sha256: str
    answers_sha256: str
    scoring_summary: str
    band_note: str
    negative_emotionality_note: str | None
    limitations: list[str]
    references: list[str]
    attribution: str


class InterestAreaOut(Model):
    area: str
    letter: str
    name: str
    short: str
    count: int = Field(description="Activities in this area the person said they would like to do.")
    total: int
    score: float = Field(description="count / total on a 0-100 scale; not a percentile.")
    enjoys: list[str]
    fields: list[str]
    reflection: str


class ExploreLinkOut(Model):
    label: str
    url: str


class InterestsOut(Model):
    code: str = Field(description="Letters of the three highest areas, highest first.")
    empty: bool = Field(description="True when no activity was chosen, so there is no meaningful code.")
    boundary_ties: list[str] = Field(description="Areas tied at the third place, so the code could differ.")
    areas: list[InterestAreaOut]
    note: str
    explore_links: list[ExploreLinkOut]
    draft: bool = Field(description="The instrument is still a draft and its results are for testing only.")


class ResultOut(Model):
    id: UUID
    session_id: UUID
    created_at: datetime
    kind: Literal["big_five", "interests"]
    traits: list[TraitResult]
    negative_emotionality: float | None
    archetypes: ArchetypesOut | None
    interests: InterestsOut | None
    quality_flags: list[str]
    methodology: Methodology
