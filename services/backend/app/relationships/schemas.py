import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RelationType = Literal["partner", "friend", "family", "colleague"]
BandOut = Literal["lower", "middle", "higher"]


class RelationshipConsentIn(BaseModel):
    accepted: Literal[True] = Field(
        description="The user agrees to show the trait bands from their latest Big Five result to the other "
        "person for as long as the link exists."
    )
    policy_version: str


class CreateInvitationIn(BaseModel):
    relation_type: RelationType
    consent: RelationshipConsentIn


class InvitationOut(BaseModel):
    id: uuid.UUID
    relation_type: RelationType
    created_at: datetime
    expires_at: datetime


class CreatedInvitation(BaseModel):
    invitation: InvitationOut
    token: str = Field(description="Shown once. Share it as a link; only its hash is stored.")


class InvitationTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=256)


class AcceptInvitationIn(InvitationTokenIn):
    consent: RelationshipConsentIn


class InvitationPreview(BaseModel):
    inviter_name: str | None = Field(description="The inviter's display name, if they set one.")
    relation_type: RelationType
    expires_at: datetime
    policy_version: str


class LinkSummary(BaseModel):
    id: uuid.UUID
    relation_type: RelationType
    other_name: str | None = Field(description="The other person's display name, if they set one.")
    you_invited: bool
    created_at: datetime


class RelationshipsOut(BaseModel):
    policy_version: str
    invitations: list[InvitationOut]
    links: list[LinkSummary]


class TraitComparisonOut(BaseModel):
    trait: str
    name: str
    you: BandOut
    them: BandOut
    pattern: Literal["similar", "some_difference", "different"]
    summary: str
    note: str
    misunderstanding: str | None
    prompt: str


class ExerciseOut(BaseModel):
    title: str
    steps: list[str]


class LinkDetail(LinkSummary):
    missing_results: list[Literal["you", "them"]] = Field(
        description="Who still needs a Big Five result before a comparison can be shown."
    )
    traits: list[TraitComparisonOut]
    note: str
    exercises: list[ExerciseOut]
    shared_goals: list[str]
