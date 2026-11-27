from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Kind = Literal["big_five", "interests", "leadership"]


class ReportSource(BaseModel):
    kind: Kind
    result_id: str
    instrument_name: str
    instrument_version: str
    completed_at: datetime


class ReportArchetype(BaseModel):
    name: str
    summary: str
    secondary: str
    weak_fit: bool
    disclaimer: str


class ReportTrait(BaseModel):
    trait: str
    name: str
    description: str
    score: float | None
    band: Literal["lower", "middle", "higher"] | None
    summary: str | None
    communication: str | None
    relationships: str | None


class ReportInterestArea(BaseModel):
    name: str
    short: str
    count: int
    total: int


class ReportInterests(BaseModel):
    code: str | None
    top: list[ReportInterestArea]
    fields: list[str]
    note: str


class ReportLeadership(BaseModel):
    most_preferred: list[str]
    least_preferred: list[str]
    even: bool
    note: str


class PlanItem(BaseModel):
    kind: Literal["program", "leadership_module"]
    id: str
    title: str
    reason: str
    href: str


class MethodologyItem(BaseModel):
    kind: Kind
    instrument_name: str
    instrument_version: str
    engine_version: str
    content_sha256: str
    answers_sha256: str
    scoring_summary: str
    band_note: str
    limitations: list[str]
    references: list[str]
    attribution: str


class ReportBody(BaseModel):
    """Everything a report shows. Built deterministically from results and versioned content."""

    report_version: str
    content_sha256: str
    sources: list[ReportSource]
    note: str
    profile: ReportArchetype | None
    traits: list[ReportTrait]
    strengths: list[str]
    development: list[str]
    interests: ReportInterests | None
    leadership: ReportLeadership | None
    values_note: str
    plan: list[PlanItem]
    methodology: list[MethodologyItem]
    limitations: list[str]


class ReportOut(BaseModel):
    id: str
    created_at: datetime
    body: ReportBody
    sha256: str


class ReportSummary(BaseModel):
    id: str
    created_at: datetime
    report_version: str
    headline: str
    kinds: list[Kind]


class ReportList(BaseModel):
    reports: list[ReportSummary]
