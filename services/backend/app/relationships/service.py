"""Relationship invitations and links. Every read and write is scoped to the two people involved;
anything else is reported as not found."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.assessments.content import ContentBundle
from app.database.models import (
    AssessmentResult,
    AssessmentSession,
    AuditEvent,
    ConsentRecord,
    RelationshipInvitation,
    RelationshipLink,
    User,
)
from app.relationships.compare import Band, compare
from app.relationships.schemas import (
    CreatedInvitation,
    ExerciseOut,
    InvitationOut,
    InvitationPreview,
    LinkDetail,
    LinkSummary,
    RelationshipConsentIn,
    RelationshipsOut,
    RelationType,
    TraitComparisonOut,
)
from app.security.consent import RELATIONSHIP_CONSENT_TYPE, RELATIONSHIP_POLICY_VERSION
from app.security.tokens import hash_token, new_token

INVITATION_TTL = timedelta(days=7)
MAX_PENDING_INVITATIONS = 10
_NOT_FOUND = ApiError(404, "invitation_not_found", "This invitation link is invalid or has expired.")


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _audit(db: Session, event: str, user_id: uuid.UUID, **details: object) -> None:
    db.add(AuditEvent(event_type=event, subject_type="user", subject_id=str(user_id), details=details))


def _consent(db: Session, user_id: uuid.UUID, consent: RelationshipConsentIn) -> ConsentRecord:
    if consent.policy_version != RELATIONSHIP_POLICY_VERSION:
        raise ApiError(
            409,
            "consent_outdated",
            "The sharing terms have changed. Please review them again.",
            {"policy_version": RELATIONSHIP_POLICY_VERSION},
        )
    record = ConsentRecord(
        user_id=user_id,
        consent_type=RELATIONSHIP_CONSENT_TYPE,
        policy_version=consent.policy_version,
        granted=True,
        age_confirmed_18_plus=True,  # accounts are 18+ only
    )
    db.add(record)
    db.flush()
    return record


def _invitation_out(inv: RelationshipInvitation) -> InvitationOut:
    return InvitationOut(
        id=inv.id,
        relation_type=cast(RelationType, inv.relation_type),
        created_at=_aware(inv.created_at),
        expires_at=_aware(inv.expires_at),
    )


def _summary(db: Session, link: RelationshipLink, user_id: uuid.UUID) -> LinkSummary:
    you_invited = link.inviter_id == user_id
    other = db.get(User, link.invitee_id if you_invited else link.inviter_id)
    return LinkSummary(
        id=link.id,
        relation_type=cast(RelationType, link.relation_type),
        other_name=other.display_name if other else None,
        you_invited=you_invited,
        created_at=_aware(link.created_at),
    )


def _pending(db: Session, token: str) -> RelationshipInvitation:
    inv = db.scalar(
        select(RelationshipInvitation).where(RelationshipInvitation.token_hash == hash_token(token))
    )
    if inv is None or _aware(inv.expires_at) <= _now():
        raise _NOT_FOUND
    return inv


def _bands(db: Session, user_id: uuid.UUID) -> dict[str, Band | None] | None:
    """Trait bands from the user's latest Big Five result, or None if they have none."""
    result = db.scalar(
        select(AssessmentResult)
        .join(AssessmentSession, AssessmentResult.session_id == AssessmentSession.id)
        .where(AssessmentSession.user_id == user_id, AssessmentResult.archetype_version.is_not(None))
        .order_by(AssessmentResult.created_at.desc())
        .limit(1)
    )
    if result is None:
        return None
    return {ts.trait: cast(Band | None, ts.band) for ts in result.trait_scores}


def overview(db: Session, user: User) -> RelationshipsOut:
    invitations = db.scalars(
        select(RelationshipInvitation)
        .where(RelationshipInvitation.inviter_id == user.id, RelationshipInvitation.expires_at > _now())
        .order_by(RelationshipInvitation.created_at.desc())
    ).all()
    links = db.scalars(
        select(RelationshipLink)
        .where(or_(RelationshipLink.inviter_id == user.id, RelationshipLink.invitee_id == user.id))
        .order_by(RelationshipLink.created_at.desc())
    ).all()
    return RelationshipsOut(
        policy_version=RELATIONSHIP_POLICY_VERSION,
        invitations=[_invitation_out(i) for i in invitations],
        links=[_summary(db, link, user.id) for link in links],
    )


def create_invitation(
    db: Session, user: User, relation_type: str, consent: RelationshipConsentIn
) -> CreatedInvitation:
    db.execute(
        delete(RelationshipInvitation).where(
            RelationshipInvitation.inviter_id == user.id, RelationshipInvitation.expires_at <= _now()
        )
    )
    pending = db.scalar(
        select(func.count())
        .select_from(RelationshipInvitation)
        .where(RelationshipInvitation.inviter_id == user.id, RelationshipInvitation.expires_at > _now())
    )
    if (pending or 0) >= MAX_PENDING_INVITATIONS:
        raise ApiError(
            429,
            "too_many_invitations",
            f"You can have up to {MAX_PENDING_INVITATIONS} open invitations. Cancel one to create another.",
        )
    record = _consent(db, user.id, consent)
    token = new_token()
    inv = RelationshipInvitation(
        inviter_id=user.id,
        relation_type=relation_type,
        token_hash=hash_token(token),
        consent_id=record.id,
        expires_at=_now() + INVITATION_TTL,
        created_at=_now(),
    )
    db.add(inv)
    db.flush()
    _audit(db, "relationship.invited", user.id, invitation_id=str(inv.id))
    db.commit()
    return CreatedInvitation(invitation=_invitation_out(inv), token=token)


def cancel_invitation(db: Session, user: User, invitation_id: uuid.UUID) -> None:
    inv = db.get(RelationshipInvitation, invitation_id)
    if inv is None or inv.inviter_id != user.id:
        raise _NOT_FOUND
    db.delete(inv)
    db.commit()


def preview(db: Session, user: User, token: str) -> InvitationPreview:
    inv = _pending(db, token)
    inviter = db.get(User, inv.inviter_id)
    return InvitationPreview(
        inviter_name=inviter.display_name if inviter else None,
        relation_type=cast(RelationType, inv.relation_type),
        expires_at=_aware(inv.expires_at),
        policy_version=RELATIONSHIP_POLICY_VERSION,
    )


def accept(db: Session, user: User, token: str, consent: RelationshipConsentIn) -> LinkSummary:
    inv = _pending(db, token)
    if inv.inviter_id == user.id:
        raise ApiError(409, "own_invitation", "You can't accept your own invitation. Share the link instead.")
    pair_key = ":".join(sorted((str(inv.inviter_id), str(user.id))))
    if db.scalar(select(RelationshipLink.id).where(RelationshipLink.pair_key == pair_key)):
        raise ApiError(409, "already_linked", "You are already comparing results with this person.")
    record = _consent(db, user.id, consent)
    link = RelationshipLink(
        inviter_id=inv.inviter_id,
        invitee_id=user.id,
        pair_key=pair_key,
        relation_type=inv.relation_type,
        inviter_consent_id=inv.consent_id,
        invitee_consent_id=record.id,
        created_at=_now(),
    )
    db.add(link)
    db.delete(inv)  # single use
    db.flush()
    _audit(db, "relationship.linked", user.id, link_id=str(link.id))
    db.commit()
    return _summary(db, link, user.id)


def _link(db: Session, user: User, link_id: uuid.UUID) -> RelationshipLink:
    link = db.get(RelationshipLink, link_id)
    if link is None or user.id not in (link.inviter_id, link.invitee_id):
        raise ApiError(404, "not_found", "Relationship not found.")
    return link


def detail(db: Session, content: ContentBundle, user: User, link_id: uuid.UUID) -> LinkDetail:
    link = _link(db, user, link_id)
    other_id = link.invitee_id if link.inviter_id == user.id else link.inviter_id
    mine, theirs = _bands(db, user.id), _bands(db, other_id)
    insights = content.relationships.data
    names = {t: text.name for t, text in content.interpretations.data.traits.items()}
    traits = compare(insights, names, mine, theirs) if mine is not None and theirs is not None else []
    missing: list[Literal["you", "them"]] = []
    if mine is None:
        missing.append("you")
    if theirs is None:
        missing.append("them")
    return LinkDetail(
        **_summary(db, link, user.id).model_dump(),
        missing_results=missing,
        traits=[TraitComparisonOut(**t.__dict__) for t in traits],
        note=insights.note,
        exercises=[ExerciseOut(title=e.title, steps=list(e.steps)) for e in insights.exercises],
        shared_goals=list(insights.shared_goals),
    )


def revoke(db: Session, user: User, link_id: uuid.UUID) -> None:
    link = _link(db, user, link_id)
    db.execute(delete(RelationshipLink).where(RelationshipLink.id == link.id))
    _audit(db, "relationship.revoked", user.id, link_id=str(link.id))
    db.commit()


def export_for(db: Session, user: User) -> dict[str, object]:
    """The user's own invitations and links for the data export. The other person's results are not
    included: they are shown on request only while the link exists."""
    data = overview(db, user)
    return {
        "invitations": [i.model_dump(mode="json") for i in data.invitations],
        "links": [link.model_dump(mode="json") for link in data.links],
    }
