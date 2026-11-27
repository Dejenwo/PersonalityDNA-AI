"""Organisations: voluntary development programmes with least-privilege roles.

An organisation sees who its members are (name, email, role, join date). It never sees answers, results,
reports, journals, goals or coaching. Members may separately opt in to having their latest Big Five bands
counted in group statistics, which are only shown for large enough groups with every band well populated.
Non-members get 404 for everything; members without the right role get 403.
"""

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.assessments.content import ContentBundle
from app.database.models import (
    AssessmentResult,
    AssessmentSession,
    AuditEvent,
    ConsentRecord,
    Organization,
    OrgInvitation,
    OrgMember,
    OrgProgram,
    OrgProgramParticipant,
    User,
)
from app.organizations.schemas import (
    BandCounts,
    CatalogItem,
    InviteRole,
    Licence,
    LicenceOut,
    OrgAnalytics,
    OrgConsentIn,
    OrgCreatedInvitation,
    OrgInvitationList,
    OrgInvitationOut,
    OrgInvitationPreview,
    OrgList,
    OrgMemberList,
    OrgMemberOut,
    OrgOut,
    OrgProgramIn,
    OrgProgramList,
    OrgProgramOut,
    OrgRole,
    OrgSummary,
    ProgramCatalog,
    ProgramItem,
    ProgramParticipation,
    TraitDistribution,
)
from app.security.consent import ORG_AGGREGATE_CONSENT_TYPE, ORG_CONSENT_TYPE, ORG_POLICY_VERSION
from app.security.tokens import hash_token, new_token

PILOT_SEATS = 25
MAX_OWNED = 3
MAX_MEMBERSHIPS = 20
MAX_OPEN_INVITATIONS = 20
MAX_PROGRAMS = 50
MIN_GROUP = 10  # opted-in members with results before any trait statistics are shown
MIN_CELL = 3  # smallest count ever shown
ANALYTICS_NOTE = (
    "Group statistics only include members who chose to share, and only appear when at least "
    f"{MIN_GROUP} of them have a Big Five result. A trait is shown only when every band has at least "
    f"{MIN_CELL} people. Bands describe tendencies, not ability or performance, and must never be used for "
    "hiring, promotion, pay or any other employment decision."
)
LEARNING_HREF = {"leadership": "/leadership", "emotional-awareness": "/emotional-awareness"}

_NOT_FOUND = ApiError(404, "not_found", "Organisation not found.")
_INVITE_NOT_FOUND = ApiError(404, "invitation_not_found", "This invitation link is invalid or has expired.")
MANAGE: tuple[OrgRole, ...] = ("owner", "admin")


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _audit(db: Session, event: str, user_id: uuid.UUID | None, org_id: uuid.UUID, **details: object) -> None:
    db.add(
        AuditEvent(
            event_type=event,
            subject_type="organisation",
            subject_id=str(org_id),
            details={"actor_id": str(user_id) if user_id else None, **details},
        )
    )


def _consent(db: Session, user_id: uuid.UUID, consent_type: str, granted: bool = True) -> ConsentRecord:
    record = ConsentRecord(
        user_id=user_id,
        consent_type=consent_type,
        policy_version=ORG_POLICY_VERSION,
        granted=granted,
        age_confirmed_18_plus=True,  # accounts are 18+ only
    )
    db.add(record)
    db.flush()
    return record


def _check_consent(consent: OrgConsentIn) -> None:
    if consent.policy_version != ORG_POLICY_VERSION:
        raise ApiError(
            409,
            "consent_outdated",
            "The organisation terms have changed. Please review them again.",
            {"policy_version": ORG_POLICY_VERSION},
        )


def _membership(db: Session, user: User, org_id: uuid.UUID) -> tuple[Organization, OrgMember]:
    m = db.scalar(select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user.id))
    org = db.get(Organization, org_id) if m else None
    if m is None or org is None:
        raise _NOT_FOUND
    return org, m


def _require(m: OrgMember, roles: tuple[OrgRole, ...]) -> None:
    if m.role not in roles:
        raise ApiError(403, "org_role_required", "Your role in this organisation can't do that.")


def _seats_used(db: Session, org_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org_id)) or 0


def licence_out(db: Session, org: Organization) -> LicenceOut:
    until = _aware(org.licensed_until) if org.licensed_until else None
    return LicenceOut(
        licence=cast(Licence, org.licence),
        seat_limit=org.seat_limit,
        seats_used=_seats_used(db, org.id),
        licensed_until=until,
        active=org.licence == "licensed" and until is not None and until > _now(),
    )


def _summary(org: Organization, m: OrgMember) -> OrgSummary:
    return OrgSummary(
        id=org.id,
        name=org.name,
        role=cast(OrgRole, m.role),
        share_aggregates=m.share_aggregates,
        joined_at=_aware(m.joined_at),
    )


def _out(db: Session, org: Organization, m: OrgMember) -> OrgOut:
    licence = licence_out(db, org)
    return OrgOut(**_summary(org, m).model_dump(), licence=licence, policy_version=ORG_POLICY_VERSION)


# --- organisations ---


def list_mine(db: Session, user: User) -> OrgList:
    rows = db.execute(
        select(Organization, OrgMember)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == user.id)
        .order_by(OrgMember.joined_at)
    ).all()
    return OrgList(organisations=[_summary(o, m) for o, m in rows], policy_version=ORG_POLICY_VERSION)


def create(db: Session, user: User, name: str, consent: OrgConsentIn) -> OrgOut:
    _check_consent(consent)
    owned = db.scalar(
        select(func.count())
        .select_from(OrgMember)
        .where(OrgMember.user_id == user.id, OrgMember.role == "owner")
    )
    if (owned or 0) >= MAX_OWNED:
        raise ApiError(409, "too_many_organisations", f"You can own up to {MAX_OWNED} organisations.")
    _membership_limit(db, user.id)
    org = Organization(
        name=name, created_by=user.id, licence="pilot", seat_limit=PILOT_SEATS, created_at=_now()
    )
    db.add(org)
    db.flush()
    record = _consent(db, user.id, ORG_CONSENT_TYPE)
    m = OrgMember(org_id=org.id, user_id=user.id, role="owner", consent_id=record.id, joined_at=_now())
    db.add(m)
    _audit(db, "org.created", user.id, org.id)
    db.commit()
    return _out(db, org, m)


def _membership_limit(db: Session, user_id: uuid.UUID) -> None:
    n = db.scalar(select(func.count()).select_from(OrgMember).where(OrgMember.user_id == user_id))
    if (n or 0) >= MAX_MEMBERSHIPS:
        raise ApiError(
            409, "too_many_memberships", f"You can belong to up to {MAX_MEMBERSHIPS} organisations."
        )


def detail(db: Session, user: User, org_id: uuid.UUID) -> OrgOut:
    org, m = _membership(db, user, org_id)
    return _out(db, org, m)


def rename(db: Session, user: User, org_id: uuid.UUID, name: str) -> OrgOut:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    org.name = name
    _audit(db, "org.renamed", user.id, org.id)
    db.commit()
    return _out(db, org, m)


def delete_org(db: Session, user: User, org_id: uuid.UUID) -> None:
    org, m = _membership(db, user, org_id)
    _require(m, ("owner",))
    _audit(db, "org.deleted", user.id, org.id)
    db.execute(delete(Organization).where(Organization.id == org.id))
    db.commit()


# --- members ---


def members(db: Session, user: User, org_id: uuid.UUID) -> OrgMemberList:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    rows = db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.org_id == org.id)
        .order_by(OrgMember.joined_at)
    ).all()
    return OrgMemberList(
        members=[
            OrgMemberOut(
                id=mem.id,
                display_name=u.display_name,
                email=u.email,
                role=cast(OrgRole, mem.role),
                joined_at=_aware(mem.joined_at),
            )
            for mem, u in rows
        ]
    )


def _target(db: Session, org_id: uuid.UUID, member_id: uuid.UUID) -> OrgMember:
    t = db.get(OrgMember, member_id)
    if t is None or t.org_id != org_id:
        raise ApiError(404, "member_not_found", "Member not found.")
    return t


def _owners(db: Session, org_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(OrgMember)
            .where(OrgMember.org_id == org_id, OrgMember.role == "owner")
        )
        or 0
    )


def set_role(
    db: Session, user: User, org_id: uuid.UUID, member_id: uuid.UUID, role: OrgRole
) -> OrgMemberList:
    """Only owners change roles, and an organisation always keeps at least one owner."""
    org, m = _membership(db, user, org_id)
    _require(m, ("owner",))
    t = _target(db, org.id, member_id)
    if t.role == "owner" and role != "owner" and _owners(db, org.id) <= 1:
        raise ApiError(409, "last_owner", "An organisation needs at least one owner.")
    old, t.role = t.role, role
    _audit(db, "org.role_changed", user.id, org.id, member_id=str(t.id), old=old, new=role)
    db.commit()
    return members(db, user, org.id)


def remove_member(db: Session, user: User, org_id: uuid.UUID, member_id: uuid.UUID) -> None:
    """Admins can remove members; only owners can remove admins or other owners."""
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    t = _target(db, org.id, member_id)
    if t.id == m.id:
        raise ApiError(409, "use_leave", "Use “leave organisation” to remove yourself.")
    if t.role != "member" and m.role != "owner":
        raise ApiError(403, "org_role_required", "Only an owner can remove an admin or owner.")
    if t.role == "owner" and _owners(db, org.id) <= 1:
        raise ApiError(409, "last_owner", "An organisation needs at least one owner.")
    _drop(db, t)
    _audit(db, "org.member_removed", user.id, org.id, member_id=str(t.id))
    db.commit()


def _drop(db: Session, m: OrgMember) -> None:
    """Delete a membership and the person's programme participation in that organisation."""
    programs = select(OrgProgram.id).where(OrgProgram.org_id == m.org_id)
    db.execute(
        delete(OrgProgramParticipant).where(
            OrgProgramParticipant.user_id == m.user_id, OrgProgramParticipant.program_id.in_(programs)
        )
    )
    db.execute(delete(OrgMember).where(OrgMember.id == m.id))


def leave(db: Session, user: User, org_id: uuid.UUID) -> None:
    org, m = _membership(db, user, org_id)
    if m.role == "owner" and _owners(db, org.id) <= 1:
        raise ApiError(
            409,
            "last_owner",
            "Make someone else an owner first, or delete the organisation if it's no longer needed.",
        )
    if m.share_aggregates:
        _consent(db, user.id, ORG_AGGREGATE_CONSENT_TYPE, granted=False)
    _drop(db, m)
    _audit(db, "org.member_left", user.id, org.id)
    db.commit()


def set_sharing(db: Session, user: User, org_id: uuid.UUID, share: bool) -> OrgOut:
    """The member's own, revocable choice. Each change is recorded as a consent event."""
    org, m = _membership(db, user, org_id)
    if m.share_aggregates != share:
        m.share_aggregates = share
        _consent(db, user.id, ORG_AGGREGATE_CONSENT_TYPE, granted=share)
        db.commit()
    return _out(db, org, m)


# --- invitations ---


def _invitation_out(inv: OrgInvitation) -> OrgInvitationOut:
    return OrgInvitationOut(
        id=inv.id,
        role=cast(InviteRole, inv.role),
        max_uses=inv.max_uses,
        uses=inv.uses,
        created_at=_aware(inv.created_at),
        expires_at=_aware(inv.expires_at),
    )


def invitations(db: Session, user: User, org_id: uuid.UUID) -> OrgInvitationList:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    rows = db.scalars(
        select(OrgInvitation)
        .where(OrgInvitation.org_id == org.id, OrgInvitation.expires_at > _now())
        .order_by(OrgInvitation.created_at.desc())
    )
    return OrgInvitationList(invitations=[_invitation_out(i) for i in rows])


def create_invitation(
    db: Session, user: User, org_id: uuid.UUID, role: InviteRole, max_uses: int, days: int
) -> OrgCreatedInvitation:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    if role == "admin" and m.role != "owner":
        raise ApiError(403, "org_role_required", "Only an owner can invite admins.")
    db.execute(
        delete(OrgInvitation).where(OrgInvitation.org_id == org.id, OrgInvitation.expires_at <= _now())
    )
    open_ = db.scalar(select(func.count()).select_from(OrgInvitation).where(OrgInvitation.org_id == org.id))
    if (open_ or 0) >= MAX_OPEN_INVITATIONS:
        raise ApiError(
            429,
            "too_many_invitations",
            f"Up to {MAX_OPEN_INVITATIONS} open links. Cancel one to create another.",
        )
    token = new_token()
    inv = OrgInvitation(
        org_id=org.id,
        created_by=user.id,
        role=role,
        token_hash=hash_token(token),
        max_uses=max_uses,
        uses=0,
        expires_at=_now() + timedelta(days=days),
        created_at=_now(),
    )
    db.add(inv)
    db.flush()
    _audit(
        db, "org.invitation_created", user.id, org.id, invitation_id=str(inv.id), role=role, max_uses=max_uses
    )
    db.commit()
    return OrgCreatedInvitation(invitation=_invitation_out(inv), token=token)


def cancel_invitation(db: Session, user: User, org_id: uuid.UUID, invitation_id: uuid.UUID) -> None:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    inv = db.get(OrgInvitation, invitation_id)
    if inv is None or inv.org_id != org.id:
        raise _INVITE_NOT_FOUND
    db.delete(inv)
    _audit(db, "org.invitation_cancelled", user.id, org.id, invitation_id=str(inv.id))
    db.commit()


def _pending(db: Session, token: str) -> tuple[OrgInvitation, Organization]:
    inv = db.scalar(select(OrgInvitation).where(OrgInvitation.token_hash == hash_token(token)))
    if inv is None or _aware(inv.expires_at) <= _now() or inv.uses >= inv.max_uses:
        raise _INVITE_NOT_FOUND
    org = db.get(Organization, inv.org_id)
    if org is None:
        raise _INVITE_NOT_FOUND
    return inv, org


def _is_member(db: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return (
        db.scalar(select(OrgMember.id).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id))
        is not None
    )


def preview(db: Session, user: User, token: str) -> OrgInvitationPreview:
    inv, org = _pending(db, token)
    return OrgInvitationPreview(
        organisation=org.name,
        role=cast(InviteRole, inv.role),
        expires_at=_aware(inv.expires_at),
        already_member=_is_member(db, org.id, user.id),
        policy_version=ORG_POLICY_VERSION,
    )


def accept(db: Session, user: User, token: str, consent: OrgConsentIn) -> OrgOut:
    inv, org = _pending(db, token)
    if _is_member(db, org.id, user.id):
        raise ApiError(409, "already_member", "You're already a member of this organisation.")
    _check_consent(consent)
    _membership_limit(db, user.id)
    # Lock the organisation row (PostgreSQL) so two people can't take the last seat at once.
    db.execute(select(Organization.id).where(Organization.id == org.id).with_for_update())
    if _seats_used(db, org.id) >= org.seat_limit:
        raise ApiError(
            409, "seat_limit", "This organisation has no free seats. Ask its administrator to add more."
        )
    record = _consent(db, user.id, ORG_CONSENT_TYPE)
    m = OrgMember(org_id=org.id, user_id=user.id, role=inv.role, consent_id=record.id, joined_at=_now())
    db.add(m)
    inv.uses += 1
    if inv.uses >= inv.max_uses:
        db.delete(inv)
    db.flush()
    _audit(db, "org.member_joined", user.id, org.id, role=inv.role)
    db.commit()
    return _out(db, org, m)


# --- programmes ---


def catalog(content: ContentBundle) -> ProgramCatalog:
    def modules(track_id: str) -> list[CatalogItem]:
        track = content.track(track_id)
        return [CatalogItem(id=x.id, title=x.title, detail=x.summary) for x in track.modules] if track else []

    return ProgramCatalog(
        growth_programs=[
            CatalogItem(id=p.id, title=p.title, detail=f"{p.days} days") for p in content.growth.data.programs
        ],
        leadership=modules("leadership"),
        emotional_awareness=modules("emotional-awareness"),
    )


def _items(content: ContentBundle, p: OrgProgram) -> list[ProgramItem]:
    items: list[ProgramItem] = []
    if p.growth_program_id:
        gp = content.growth.data.program(p.growth_program_id)
        if gp is not None:
            items.append(ProgramItem(kind="growth", title=gp.title, href=f"/growth/{gp.id}"))
    for ref in p.learning or []:
        track = content.track(ref["track"])
        mod = track.module(ref["module"]) if track else None
        if mod is not None:
            items.append(
                ProgramItem(kind="learning", title=mod.title, href=f"{LEARNING_HREF[ref['track']]}/{mod.id}")
            )
    return items


def _program_out(content: ContentBundle, p: OrgProgram, joined: bool) -> OrgProgramOut:
    return OrgProgramOut(
        id=p.id,
        title=p.title,
        description=p.description,
        items=_items(content, p),
        joined=joined,
        created_at=_aware(p.created_at),
    )


def programs(db: Session, content: ContentBundle, user: User, org_id: uuid.UUID) -> OrgProgramList:
    org, _ = _membership(db, user, org_id)
    rows = db.scalars(select(OrgProgram).where(OrgProgram.org_id == org.id).order_by(OrgProgram.created_at))
    mine = set(
        db.scalars(
            select(OrgProgramParticipant.program_id)
            .join(OrgProgram, OrgProgram.id == OrgProgramParticipant.program_id)
            .where(OrgProgramParticipant.user_id == user.id, OrgProgram.org_id == org.id)
        )
    )
    return OrgProgramList(programs=[_program_out(content, p, p.id in mine) for p in rows])


def create_program(
    db: Session, content: ContentBundle, user: User, org_id: uuid.UUID, body: OrgProgramIn
) -> OrgProgramOut:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    if body.growth_program_id and content.growth.data.program(body.growth_program_id) is None:
        raise ApiError(422, "unknown_program", "That growth programme doesn't exist.")
    refs = []
    for ref in body.learning:
        track = content.track(ref.track)
        if track is None or track.module(ref.module) is None:
            raise ApiError(422, "unknown_module", "One of the learning modules doesn't exist.")
        refs.append({"track": ref.track, "module": ref.module})
    if not body.growth_program_id and not refs:
        raise ApiError(422, "empty_program", "Add a growth programme or at least one learning module.")
    count = db.scalar(select(func.count()).select_from(OrgProgram).where(OrgProgram.org_id == org.id))
    if (count or 0) >= MAX_PROGRAMS:
        raise ApiError(409, "too_many_programs", f"An organisation can have up to {MAX_PROGRAMS} programmes.")
    p = OrgProgram(
        org_id=org.id,
        title=body.title,
        description=body.description.strip(),
        growth_program_id=body.growth_program_id,
        learning=refs,
        created_by=user.id,
        created_at=_now(),
    )
    db.add(p)
    db.flush()
    _audit(db, "org.program_created", user.id, org.id, program_id=str(p.id))
    db.commit()
    return _program_out(content, p, False)


def _program(db: Session, org_id: uuid.UUID, program_id: uuid.UUID) -> OrgProgram:
    p = db.get(OrgProgram, program_id)
    if p is None or p.org_id != org_id:
        raise ApiError(404, "program_not_found", "Programme not found.")
    return p


def delete_program(db: Session, user: User, org_id: uuid.UUID, program_id: uuid.UUID) -> None:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    p = _program(db, org.id, program_id)
    db.execute(delete(OrgProgram).where(OrgProgram.id == p.id))
    _audit(db, "org.program_deleted", user.id, org.id, program_id=str(p.id))
    db.commit()


def join_program(
    db: Session, content: ContentBundle, user: User, org_id: uuid.UUID, program_id: uuid.UUID, join: bool
) -> OrgProgramOut:
    """Joining is voluntary and private to the member: the organisation only ever sees a suppressed count."""
    org, _ = _membership(db, user, org_id)
    p = _program(db, org.id, program_id)
    existing = db.scalar(
        select(OrgProgramParticipant).where(
            OrgProgramParticipant.program_id == p.id, OrgProgramParticipant.user_id == user.id
        )
    )
    if join and existing is None:
        db.add(OrgProgramParticipant(program_id=p.id, user_id=user.id, joined_at=_now()))
    elif not join and existing is not None:
        db.delete(existing)
    db.commit()
    return _program_out(content, p, join)


# --- analytics ---


def _latest_bands(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, str | None]]:
    """Each person's latest Big Five result, as trait -> band."""
    if not user_ids:
        return {}
    rows = db.execute(
        select(AssessmentSession.user_id, AssessmentResult)
        .join(AssessmentResult, AssessmentResult.session_id == AssessmentSession.id)
        .where(AssessmentSession.user_id.in_(user_ids), AssessmentResult.archetype_version.is_not(None))
        .order_by(AssessmentResult.created_at.desc())
    ).all()
    out: dict[uuid.UUID, dict[str, str | None]] = {}
    for uid, result in rows:
        if uid is not None and uid not in out:
            out[uid] = {ts.trait: ts.band for ts in result.trait_scores}
    return out


def suppress(counts: Counter[str]) -> BandCounts | None:
    """Show a trait only when every band holds at least MIN_CELL people. Anything less could single someone
    out, or let a hidden band be worked out from the total."""
    if any(counts[b] < MIN_CELL for b in ("lower", "middle", "higher")):
        return None
    return BandCounts(lower=counts["lower"], middle=counts["middle"], higher=counts["higher"])


def analytics(db: Session, content: ContentBundle, user: User, org_id: uuid.UUID) -> OrgAnalytics:
    org, m = _membership(db, user, org_id)
    _require(m, MANAGE)
    sharing = list(
        db.scalars(select(OrgMember.user_id).where(OrgMember.org_id == org.id, OrgMember.share_aggregates))
    )
    bands = _latest_bands(db, sharing)
    n = len(bands)
    names = {t: text.name for t, text in content.interpretations.data.traits.items()}
    traits: list[TraitDistribution] = []
    if n >= MIN_GROUP:
        for trait, name in names.items():
            counts = Counter(band for b in bands.values() if (band := b.get(trait)))
            traits.append(TraitDistribution(trait=trait, name=name, bands=suppress(counts)))
    participation = []
    org_programs = select(OrgProgram).where(OrgProgram.org_id == org.id).order_by(OrgProgram.created_at)
    for p in db.scalars(org_programs):
        k = (
            db.scalar(
                select(func.count())
                .select_from(OrgProgramParticipant)
                .where(OrgProgramParticipant.program_id == p.id)
            )
            or 0
        )
        shown = k if k >= MIN_CELL else None
        participation.append(ProgramParticipation(id=p.id, title=p.title, participants=shown))
    return OrgAnalytics(
        members=_seats_used(db, org.id),
        seat_limit=org.seat_limit,
        min_group=MIN_GROUP,
        min_cell=MIN_CELL,
        consenting_members=n if n >= MIN_GROUP else None,
        traits=traits,
        programs=participation,
        note=ANALYTICS_NOTE,
    )


# --- account lifecycle ---


def before_account_deletion(db: Session, user_id: uuid.UUID) -> None:
    """Keep organisations usable when their last owner deletes their account: the longest-serving admin (or
    member) becomes owner. An organisation with nobody else in it is deleted."""
    owned = select(OrgMember).where(OrgMember.user_id == user_id, OrgMember.role == "owner")
    for m in list(db.scalars(owned)):
        if _owners(db, m.org_id) > 1:
            continue
        others = list(
            db.scalars(
                select(OrgMember)
                .where(OrgMember.org_id == m.org_id, OrgMember.user_id != user_id)
                .order_by(OrgMember.joined_at)
            )
        )
        if not others:
            db.execute(delete(Organization).where(Organization.id == m.org_id))
            continue
        heir = next((o for o in others if o.role == "admin"), others[0])
        heir.role = "owner"
        _audit(db, "org.owner_succeeded", None, m.org_id, member_id=str(heir.id))


def managers(db: Session, org_id: uuid.UUID) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(OrgMember, OrgMember.user_id == User.id)
            .where(OrgMember.org_id == org_id, OrgMember.role.in_(MANAGE))
        )
    )


def export_for(db: Session, user: User) -> list[dict[str, object]]:
    return [s.model_dump(mode="json") for s in list_mine(db, user).organisations]
