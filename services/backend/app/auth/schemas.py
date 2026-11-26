from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field

from app.api.schemas import Model


class RegisterIn(Model):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    display_name: str | None = Field(default=None, max_length=80)
    accepted_terms: bool
    age_confirmed_18_plus: bool
    policy_version: str = Field(max_length=32)


class EmailIn(Model):
    email: EmailStr


class TokenIn(Model):
    token: str = Field(min_length=1, max_length=256)


class LoginIn(Model):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    client: Literal["web", "mobile"] = "web"


class RefreshIn(Model):
    refresh_token: str | None = Field(default=None, max_length=256, description="Mobile clients only.")


class ResetConfirmIn(Model):
    token: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class UserOut(Model):
    id: UUID
    email: str
    display_name: str | None
    locale: str
    email_verified: bool
    created_at: datetime


class AuthOut(Model):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (OAuth token type, not a secret)
    expires_at: datetime
    user: UserOut
    refresh_token: str | None = Field(default=None, description="Returned only to mobile clients.")


class MessageOut(Model):
    message: str


class UpdateMeIn(Model):
    display_name: str | None = Field(default=None, max_length=80)
    locale: Literal["en"] | None = None


class ClaimIn(Model):
    session_id: UUID
    resume_token: str = Field(min_length=1, max_length=256)


class DeleteAccountIn(Model):
    password: str = Field(min_length=1, max_length=256)


class HistoryItem(Model):
    session_id: UUID
    instrument_id: str
    instrument_name: str
    status: Literal["in_progress", "completed", "abandoned"]
    started_at: datetime
    completed_at: datetime | None
    result_id: UUID | None
    primary_archetype: str | None
    answered: int
    total: int


class HistoryOut(Model):
    items: list[HistoryItem]


class OutboxItem(Model):
    to: str
    subject: str
    text: str
    kind: str
    sent_at: datetime


class OutboxOut(Model):
    items: list[OutboxItem]
