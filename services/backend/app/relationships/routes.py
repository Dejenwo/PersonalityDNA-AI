"""Relationship comparison endpoints. Signed-in, verified users only."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.database.models import User
from app.relationships import service
from app.relationships.schemas import (
    AcceptInvitationIn,
    CreatedInvitation,
    CreateInvitationIn,
    InvitationPreview,
    InvitationTokenIn,
    LinkDetail,
    LinkSummary,
    RelationshipsOut,
)

router = APIRouter(
    prefix="/api/v1/relationships",
    tags=["relationships"],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse}}


def verified_user(user: CurrentUser) -> User:
    if user.email_verified_at is None:
        raise ApiError(403, "email_not_verified", "Please verify your email address to compare results.")
    return user


Verified = Annotated[User, Depends(verified_user)]


@router.get("", response_model=RelationshipsOut)
def overview(user: Verified, db: Db) -> RelationshipsOut:
    return service.overview(db, user)


@router.post(
    "/invitations",
    response_model=CreatedInvitation,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def create_invitation(
    body: CreateInvitationIn, request: Request, user: Verified, db: Db
) -> CreatedInvitation:
    """Inviting is part of Premium once billing is enforced; accepting an invitation is always free."""
    request.app.state.entitlements.require(db, user.id, "relationships")
    return service.create_invitation(db, user, body.relation_type, body.consent)


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=NOT_FOUND,
)
def cancel_invitation(invitation_id: uuid.UUID, user: Verified, db: Db) -> Response:
    service.cancel_invitation(db, user, invitation_id)
    return Response(status_code=204)


@router.post("/invitations/preview", response_model=InvitationPreview, responses=NOT_FOUND)
def preview_invitation(body: InvitationTokenIn, user: Verified, db: Db) -> InvitationPreview:
    """Who is inviting and as what, so the person can decide. The token travels in the body, never the URL."""
    return service.preview(db, user, body.token)


@router.post(
    "/invitations/accept",
    response_model=LinkSummary,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}},
)
def accept_invitation(body: AcceptInvitationIn, user: Verified, db: Db) -> LinkSummary:
    return service.accept(db, user, body.token, body.consent)


@router.get("/{link_id}", response_model=LinkDetail, responses=NOT_FOUND)
def get_link(link_id: uuid.UUID, user: Verified, db: Db, content: Content) -> LinkDetail:
    return service.detail(db, content, user, link_id)


@router.delete(
    "/{link_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, responses=NOT_FOUND
)
def revoke_link(link_id: uuid.UUID, user: Verified, db: Db) -> Response:
    """Either person can end the comparison at any time. The link is deleted for both."""
    service.revoke(db, user, link_id)
    return Response(status_code=204)
