"""Organisation endpoints. Signed-in, verified users only. Non-members get 404; members whose role doesn't
allow an action get 403."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.database.models import User
from app.organizations import service
from app.organizations.schemas import (
    CreateOrgIn,
    OrgAcceptIn,
    OrgAnalytics,
    OrgCreatedInvitation,
    OrgInvitationIn,
    OrgInvitationList,
    OrgInvitationPreview,
    OrgList,
    OrgMemberList,
    OrgOut,
    OrgProgramIn,
    OrgProgramList,
    OrgProgramOut,
    OrgRoleIn,
    OrgTokenIn,
    ProgramCatalog,
    RenameOrgIn,
    SharingIn,
)

router = APIRouter(
    prefix="/api/v1/orgs",
    tags=["organisations"],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": ErrorResponse}}
NO_CONTENT: dict[str, Any] = {"status_code": status.HTTP_204_NO_CONTENT, "response_class": Response}


def verified_user(user: CurrentUser) -> User:
    if user.email_verified_at is None:
        raise ApiError(403, "email_not_verified", "Please verify your email address to use organisations.")
    return user


Verified = Annotated[User, Depends(verified_user)]


@router.get("", response_model=OrgList)
def list_mine(user: Verified, db: Db) -> OrgList:
    return service.list_mine(db, user)


@router.post("", response_model=OrgOut, status_code=status.HTTP_201_CREATED, responses=CONFLICT)
def create(body: CreateOrgIn, user: Verified, db: Db) -> OrgOut:
    """Starts as a pilot with a fixed number of seats. You become its owner."""
    return service.create(db, user, body.name, body.consent)


@router.get("/catalog", response_model=ProgramCatalog)
def catalog(_: Verified, content: Content) -> ProgramCatalog:
    return service.catalog(content)


@router.post("/invitations/preview", response_model=OrgInvitationPreview)
def preview(body: OrgTokenIn, user: Verified, db: Db) -> OrgInvitationPreview:
    """The token travels in the body, never the URL."""
    return service.preview(db, user, body.token)


@router.post("/invitations/accept", response_model=OrgOut, responses=CONFLICT)
def accept(body: OrgAcceptIn, user: Verified, db: Db) -> OrgOut:
    return service.accept(db, user, body.token, body.consent)


@router.get("/{org_id}", response_model=OrgOut)
def detail(org_id: uuid.UUID, user: Verified, db: Db) -> OrgOut:
    return service.detail(db, user, org_id)


@router.patch("/{org_id}", response_model=OrgOut)
def rename(org_id: uuid.UUID, body: RenameOrgIn, user: Verified, db: Db) -> OrgOut:
    return service.rename(db, user, org_id, body.name)


@router.delete("/{org_id}", **NO_CONTENT)
def delete_org(org_id: uuid.UUID, user: Verified, db: Db) -> Response:
    service.delete_org(db, user, org_id)
    return Response(status_code=204)


@router.delete("/{org_id}/membership", responses=CONFLICT, **NO_CONTENT)
def leave(org_id: uuid.UUID, user: Verified, db: Db) -> Response:
    """Leave at any time. Your programme participation in this organisation is removed too."""
    service.leave(db, user, org_id)
    return Response(status_code=204)


@router.put("/{org_id}/membership/sharing", response_model=OrgOut)
def set_sharing(org_id: uuid.UUID, body: SharingIn, user: Verified, db: Db) -> OrgOut:
    """Opt in or out of having your latest Big Five bands counted in suppressed group statistics."""
    return service.set_sharing(db, user, org_id, body.share_aggregates)


@router.get("/{org_id}/members", response_model=OrgMemberList)
def members(org_id: uuid.UUID, user: Verified, db: Db) -> OrgMemberList:
    return service.members(db, user, org_id)


@router.put("/{org_id}/members/{member_id}/role", response_model=OrgMemberList, responses=CONFLICT)
def set_role(
    org_id: uuid.UUID, member_id: uuid.UUID, body: OrgRoleIn, user: Verified, db: Db
) -> OrgMemberList:
    return service.set_role(db, user, org_id, member_id, body.role)


@router.delete("/{org_id}/members/{member_id}", responses=CONFLICT, **NO_CONTENT)
def remove_member(org_id: uuid.UUID, member_id: uuid.UUID, user: Verified, db: Db) -> Response:
    service.remove_member(db, user, org_id, member_id)
    return Response(status_code=204)


@router.get("/{org_id}/invitations", response_model=OrgInvitationList)
def invitations(org_id: uuid.UUID, user: Verified, db: Db) -> OrgInvitationList:
    return service.invitations(db, user, org_id)


@router.post(
    "/{org_id}/invitations",
    response_model=OrgCreatedInvitation,
    status_code=status.HTTP_201_CREATED,
    responses={429: {"model": ErrorResponse}},
)
def create_invitation(
    org_id: uuid.UUID, body: OrgInvitationIn, user: Verified, db: Db
) -> OrgCreatedInvitation:
    return service.create_invitation(db, user, org_id, body.role, body.max_uses, body.days)


@router.delete("/{org_id}/invitations/{invitation_id}", **NO_CONTENT)
def cancel_invitation(org_id: uuid.UUID, invitation_id: uuid.UUID, user: Verified, db: Db) -> Response:
    service.cancel_invitation(db, user, org_id, invitation_id)
    return Response(status_code=204)


@router.get("/{org_id}/programs", response_model=OrgProgramList)
def programs(org_id: uuid.UUID, user: Verified, db: Db, content: Content) -> OrgProgramList:
    return service.programs(db, content, user, org_id)


@router.post(
    "/{org_id}/programs",
    response_model=OrgProgramOut,
    status_code=status.HTTP_201_CREATED,
    responses={**CONFLICT, 422: {"model": ErrorResponse}},
)
def create_program(
    org_id: uuid.UUID, body: OrgProgramIn, user: Verified, db: Db, content: Content
) -> OrgProgramOut:
    return service.create_program(db, content, user, org_id, body)


@router.delete("/{org_id}/programs/{program_id}", **NO_CONTENT)
def delete_program(org_id: uuid.UUID, program_id: uuid.UUID, user: Verified, db: Db) -> Response:
    service.delete_program(db, user, org_id, program_id)
    return Response(status_code=204)


@router.put("/{org_id}/programs/{program_id}/participation", response_model=OrgProgramOut)
def join_program(
    org_id: uuid.UUID, program_id: uuid.UUID, user: Verified, db: Db, content: Content
) -> OrgProgramOut:
    return service.join_program(db, content, user, org_id, program_id, True)


@router.delete("/{org_id}/programs/{program_id}/participation", response_model=OrgProgramOut)
def leave_program(
    org_id: uuid.UUID, program_id: uuid.UUID, user: Verified, db: Db, content: Content
) -> OrgProgramOut:
    return service.join_program(db, content, user, org_id, program_id, False)


@router.get("/{org_id}/analytics", response_model=OrgAnalytics)
def analytics(org_id: uuid.UUID, user: Verified, db: Db, content: Content) -> OrgAnalytics:
    """Owners and admins only. Counts and suppressed band distributions; never an individual's result."""
    return service.analytics(db, content, user, org_id)
