import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.coaching.safety import MAX_MESSAGE_CHARS

Topic = Literal[
    "results", "communication", "relationships", "career", "leadership", "emotions", "goals", "general"
]


class CoachConsentIn(BaseModel):
    accepted: Literal[True] = Field(
        description="The user agrees that the coach may send their messages and selected results to the "
        "configured AI provider."
    )
    policy_version: str


class CreateConversationIn(BaseModel):
    consent: CoachConsentIn
    topic: Topic = "results"
    use_results: bool = Field(default=True, description="Let the coach use assessment results.")
    result_id: uuid.UUID | None = Field(
        default=None, description="Result to use. Defaults to the user's most recent result."
    )


class SendMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class CoachMessageOut(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    kind: Literal["message", "crisis_support", "safety_replacement", "unavailable"]
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: uuid.UUID
    topic: Topic
    title: str
    uses_results: bool
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationOut(ConversationSummary):
    messages: list[CoachMessageOut]


class ConversationList(BaseModel):
    items: list[ConversationSummary]


class CoachStatus(BaseModel):
    enabled: bool
    demo_mode: bool = Field(description="True when replies come from the built-in stand-in, not an AI model.")
    email_verified: bool
    consent_policy_version: str
    daily_limit: int
    used: int = Field(description="Messages counted in the last 24 hours.")
    remaining: int
    resets_at: datetime | None = Field(
        description="When the next message becomes available, if at the limit."
    )
    has_results: bool
