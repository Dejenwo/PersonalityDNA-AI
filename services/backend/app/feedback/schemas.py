from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Kind = Literal["bug", "idea", "content", "accessibility", "other"]
Status = Literal["new", "planned", "fixed", "closed"]


class FeedbackIn(BaseModel):
    kind: Kind
    message: str = Field(min_length=10, max_length=2000)
    page: str | None = Field(default=None, max_length=200)
    app_version: str | None = Field(default=None, max_length=40)
    contact_ok: bool = False

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Please write at least 10 characters.")
        return v

    @field_validator("page")
    @classmethod
    def _path_only(cls, v: str | None) -> str | None:
        """Keep the path of the screen only: query strings and fragments can hold tokens."""
        if v is None:
            return None
        path = v.split("?", 1)[0].split("#", 1)[0].strip()
        return path if path.startswith("/") and "//" not in path else None


class FeedbackOut(BaseModel):
    id: str
    kind: Kind
    message: str
    page: str | None
    status: Status
    created_at: datetime


class FeedbackList(BaseModel):
    items: list[FeedbackOut]


class AdminFeedback(FeedbackOut):
    app_version: str | None
    signed_in: bool
    # Only when the sender agreed to be contacted.
    user_id: str | None
    updated_at: datetime


class AdminFeedbackList(BaseModel):
    items: list[AdminFeedback]
    counts: dict[str, int]
    next_before: datetime | None


class FeedbackStatusIn(BaseModel):
    status: Status
