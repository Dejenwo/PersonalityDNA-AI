from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.assessments.content import JournalKind

MAX_BODY = 20_000
MAX_TAGS = 10


class EntryIn(BaseModel):
    kind: JournalKind = "daily"
    title: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=MAX_BODY)
    mood: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS)
    entry_date: date | None = None


class EntryPatch(BaseModel):
    """Only the fields that are sent change. Send null to clear the title or mood."""

    kind: JournalKind | None = None
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=MAX_BODY)
    mood: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS)
    entry_date: date | None = None


class EntryOut(BaseModel):
    id: str
    kind: JournalKind
    title: str | None
    body: str
    mood: int | None
    tags: list[str]
    entry_date: date
    created_at: datetime
    updated_at: datetime


class EntryList(BaseModel):
    items: list[EntryOut]
    next_cursor: str | None


class SearchIn(BaseModel):
    """Search runs on the server after decryption. It is a POST so the words never appear in URLs or logs."""

    q: str | None = Field(default=None, max_length=200)
    tag: str | None = Field(default=None, max_length=32)
    kind: JournalKind | None = None
    date_from: date | None = None
    date_to: date | None = None
    cursor: str | None = Field(default=None, max_length=32)
    limit: int = Field(default=50, ge=1, le=100)


class KindOut(BaseModel):
    id: JournalKind
    label: str
    description: str
    prompts: list[str]


class PromptsOut(BaseModel):
    note: str
    support_note: str
    mood_scale: list[str]
    kinds: list[KindOut]


class TagCount(BaseModel):
    tag: str
    count: int


class TagsOut(BaseModel):
    tags: list[TagCount]


class DeleteAllIn(BaseModel):
    confirm: Literal[True]
