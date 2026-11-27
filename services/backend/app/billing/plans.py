"""Plan configuration. Prices and plan contents live in plans.v1.json, not in feature code; features ask the
entitlement service, never a plan id."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

Feature = Literal["report_pdf", "growth_programs", "relationships", "expanded_coaching"]


class FeatureInfo(BaseModel):
    id: Feature
    label: str


class Plan(BaseModel):
    id: str
    name: str
    price_cents: int
    interval: Literal["month", "year"] | None
    features: list[Feature]
    coach_daily_messages: int
    highlights: list[str]


class PlanConfig(BaseModel):
    version: str
    currency: str
    note: str
    free_note: str
    features: list[FeatureInfo]
    plans: list[Plan]
    organisation_plan: Plan

    @model_validator(mode="after")
    def _check(self) -> "PlanConfig":
        ids = [p.id for p in self.plans]
        if len(set(ids)) != len(ids) or "free" not in ids:
            raise ValueError("plan ids must be unique and include 'free'")
        if self.plan("free").features or self.plan("free").price_cents != 0:
            raise ValueError("the free plan has no paid features and no price")
        if {f.id for f in self.features} != {f for p in self.plans for f in p.features}:
            raise ValueError("every feature must be described and used by a plan")
        if self.organisation_plan.id in ids or self.organisation_plan.price_cents != 0:
            raise ValueError("the organisation plan is separate from personal plans and priced by agreement")
        return self

    def plan(self, plan_id: str) -> Plan:
        for p in self.plans:
            if p.id == plan_id:
                return p
        raise KeyError(plan_id)

    def paid(self) -> list[Plan]:
        return [p for p in self.plans if p.price_cents > 0]


@lru_cache
def load_plans(path: Path = Path(__file__).with_name("plans.v1.json")) -> PlanConfig:
    return PlanConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))
