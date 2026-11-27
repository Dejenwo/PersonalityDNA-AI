import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

OrgRole = Literal["owner", "admin", "member"]
InviteRole = Literal["admin", "member"]
Licence = Literal["pilot", "licensed"]
BandOut = Literal["lower", "middle", "higher"]


class OrgConsentIn(BaseModel):
    accepted: Literal[True] = Field(
        description="The person agrees that the organisation sees their name, email, role and join date. "
        "It never sees answers, results, reports, journals, goals or coaching."
    )
    policy_version: str


def _clean(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("must not be blank")
    return v


class CreateOrgIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    consent: OrgConsentIn

    _name = field_validator("name")(_clean)


class RenameOrgIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)

    _name = field_validator("name")(_clean)


class LicenceOut(BaseModel):
    licence: Licence
    seat_limit: int
    seats_used: int
    licensed_until: datetime | None
    active: bool = Field(description="True while a paid licence gives members Premium features.")


class OrgSummary(BaseModel):
    id: uuid.UUID
    name: str
    role: OrgRole
    share_aggregates: bool
    joined_at: datetime


class OrgOut(OrgSummary):
    licence: LicenceOut
    policy_version: str


class OrgList(BaseModel):
    organisations: list[OrgSummary]
    policy_version: str


class OrgMemberOut(BaseModel):
    """What an organisation sees about a member. Deliberately no results and no consent status."""

    id: uuid.UUID
    display_name: str | None
    email: str
    role: OrgRole
    joined_at: datetime


class OrgMemberList(BaseModel):
    members: list[OrgMemberOut]


class OrgRoleIn(BaseModel):
    role: OrgRole


class SharingIn(BaseModel):
    share_aggregates: bool


class OrgInvitationIn(BaseModel):
    role: InviteRole = "member"
    max_uses: int = Field(default=1, ge=1, le=500)
    days: int = Field(default=14, ge=1, le=30)


class OrgInvitationOut(BaseModel):
    id: uuid.UUID
    role: InviteRole
    max_uses: int
    uses: int
    created_at: datetime
    expires_at: datetime


class OrgCreatedInvitation(BaseModel):
    invitation: OrgInvitationOut
    token: str = Field(description="Shown once. Share it as a link; only its hash is stored.")


class OrgInvitationList(BaseModel):
    invitations: list[OrgInvitationOut]


class OrgTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=256)


class OrgAcceptIn(OrgTokenIn):
    consent: OrgConsentIn


class OrgInvitationPreview(BaseModel):
    organisation: str
    role: InviteRole
    expires_at: datetime
    already_member: bool
    policy_version: str


class LearningRef(BaseModel):
    track: Literal["leadership", "emotional-awareness"]
    module: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64)


class OrgProgramIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    growth_program_id: str | None = Field(default=None, pattern=r"^[a-z0-9-]+$", max_length=64)
    learning: list[LearningRef] = Field(default_factory=list, max_length=6)

    _title = field_validator("title")(_clean)


class ProgramItem(BaseModel):
    kind: Literal["growth", "learning"]
    title: str
    href: str


class OrgProgramOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    items: list[ProgramItem]
    joined: bool
    created_at: datetime


class OrgProgramList(BaseModel):
    programs: list[OrgProgramOut]


class CatalogItem(BaseModel):
    id: str
    title: str
    detail: str


class ProgramCatalog(BaseModel):
    """What a programme can be built from: the versioned growth programmes and learning modules."""

    growth_programs: list[CatalogItem]
    leadership: list[CatalogItem]
    emotional_awareness: list[CatalogItem]


class BandCounts(BaseModel):
    lower: int
    middle: int
    higher: int


class TraitDistribution(BaseModel):
    trait: str
    name: str
    bands: BandCounts | None = Field(
        description="Null unless every band holds at least the cell threshold, so no band (and no person) "
        "can be singled out or worked out from the others."
    )


class ProgramParticipation(BaseModel):
    id: uuid.UUID
    title: str
    participants: int | None = Field(description="Null when fewer than the cell threshold.")


class OrgAnalytics(BaseModel):
    members: int
    seat_limit: int
    min_group: int
    min_cell: int
    consenting_members: int | None = Field(
        description="Members who opted in and have a Big Five result. Null below the group threshold."
    )
    traits: list[TraitDistribution]
    programs: list[ProgramParticipation]
    note: str
