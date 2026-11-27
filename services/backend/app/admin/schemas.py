from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.admin.roles import Role
from app.i18n.locales import Locale


class AdminMe(BaseModel):
    roles: list[Role]
    permissions: list[str]


class UserSummary(BaseModel):
    """Account metadata only. Never answers, journal text, coaching messages or report contents."""

    id: str
    email: str
    created_at: datetime
    email_verified: bool
    status: Literal["active", "disabled"]
    plan_id: str


class UserDetail(UserSummary):
    display_name: str | None
    completed_assessments: int
    reports: int
    subscriptions: list["AdminSubscription"]
    admin_roles: list[Role]


class AdminSubscription(BaseModel):
    id: str
    provider: str
    plan_id: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool


class UserList(BaseModel):
    users: list[UserSummary]


class StatusIn(BaseModel):
    status: Literal["active", "disabled"]
    reason: str = Field(min_length=3, max_length=500)


class GrantIn(BaseModel):
    plan_id: str
    days: int = Field(ge=1, le=366)
    reason: str = Field(min_length=3, max_length=500)


class RoleIn(BaseModel):
    role: Role


class CountWindow(BaseModel):
    total: int
    last_7_days: int
    last_30_days: int


class Metrics(BaseModel):
    """Aggregates only. Small counts are shown as they are: this is an internal, permissioned view."""

    generated_at: datetime
    users: CountWindow
    verified_users: int
    disabled_users: int
    completed_assessments: CountWindow
    assessments_by_instrument: dict[str, int]
    active_subscriptions_by_plan: dict[str, int]
    active_subscriptions_by_provider: dict[str, int]
    estimated_monthly_revenue_cents: int
    revenue_note: str
    reports_created: CountWindow
    active_share_cards: int
    coach_turns: CountWindow
    coach_tokens_30_days: dict[str, int]
    coach_cost_30_days_usd: float | None
    coach_cost_per_active_user_30_days_usd: float | None
    coach_active_users_30_days: int
    cost_note: str
    feature_users: dict[str, int]


class ContentFile(BaseModel):
    name: str
    version: str
    locale: str | None
    sha256: str


class InstrumentInfo(BaseModel):
    id: str
    version: str
    name: str
    family: str
    tier: str
    status: str
    items: int
    license: str
    references: list[str]
    sha256: str
    locale: str
    adaptation: str | None = Field(description="Review status of a translated version; null for the source.")


class ContentOverview(BaseModel):
    engine_version: str
    report_version: str
    coach_prompt: str
    plans_version: str
    instruments: list[InstrumentInfo]
    files: list[ContentFile]
    note: str
    languages: list[Locale]
    languages_note: str


class AuditItem(BaseModel):
    id: str
    event_type: str
    subject_type: str
    subject_id: str
    details: dict[str, object]
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditItem]
    next_before: datetime | None


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    environment: str
    coach_provider: str
    coach_enabled: bool
    email_provider: str
    billing_enforced: bool
    stripe_configured: bool
    revenuecat_configured: bool
    content_instruments: int


class AdminOrg(BaseModel):
    """Organisation metadata and licence. Never member results or programme participation by name."""

    id: str
    name: str
    members: int
    owners: int
    licence: Literal["pilot", "licensed"]
    seat_limit: int
    licensed_until: datetime | None
    licence_active: bool
    created_at: datetime


class AdminOrgList(BaseModel):
    organisations: list[AdminOrg]


class LicenceIn(BaseModel):
    licence: Literal["pilot", "licensed"]
    seat_limit: int = Field(ge=1, le=100_000)
    days: int | None = Field(
        default=None, ge=1, le=1096, description="Licence length; required when licensed."
    )
    reason: str = Field(min_length=3, max_length=500)
