"""ORM models for the assessment vertical slice.

Tables for later phases (profiles, coaching, growth, subscriptions...) are designed in
docs/DATABASE_DESIGN.md and will be added with their own migrations.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AssessmentInstrument(Base):
    __tablename__ = "assessment_instruments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssessmentVersion(Base):
    __tablename__ = "assessment_versions"
    __table_args__ = (UniqueConstraint("instrument_id", "version", name="uq_assessment_version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_instruments.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[str] = mapped_column(String(32))
    content_sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status in ('active','disabled')", name="ck_user_status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    # Stored lower-cased; uniqueness is case-insensitive by construction.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    locale: Mapped[str] = mapped_column(String(16), default="en")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthToken(Base):
    """Single-use emailed tokens (email verification, password reset). Only hashes are stored."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint("purpose in ('verify_email','reset_password')", name="ck_auth_token_purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    """Rotating refresh tokens. Reusing a rotated token revokes the whole family (theft detection)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    # Kept (unlinked) after account deletion as proof that consent was given.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_consent_records_user_id_users"),
        nullable=True,
        index=True,
    )
    consent_type: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(32))
    granted: Mapped[bool]
    age_confirmed_18_plus: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"
    __table_args__ = (
        CheckConstraint("status in ('in_progress','completed','abandoned')", name="ck_session_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_versions.id", ondelete="RESTRICT"), index=True
    )
    # Set when an account claims the session; deleting the account deletes its sessions.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_assessment_sessions_user_id_users"),
        nullable=True,
        index=True,
    )
    consent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_records.id", ondelete="RESTRICT"), index=True
    )
    # SHA-256 of the resume token. The token itself is never stored.
    token_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    locale: Mapped[str] = mapped_column(String(16), default="en")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    version: Mapped[AssessmentVersion] = relationship()
    responses: Mapped[list["AssessmentResponse"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    result: Mapped["AssessmentResult | None"] = relationship(back_populates="session", uselist=False)


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"
    __table_args__ = (
        UniqueConstraint("session_id", "item_id", name="uq_response_item"),
        CheckConstraint("value between 1 and 7", name="ck_response_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[str] = mapped_column(String(64))
    value: Mapped[int] = mapped_column(Integer)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[AssessmentSession] = relationship(back_populates="responses")


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), unique=True
    )
    engine_version: Mapped[str] = mapped_column(String(32))
    instrument_id: Mapped[str] = mapped_column(String(64))
    instrument_version: Mapped[str] = mapped_column(String(32))
    content_sha256: Mapped[str] = mapped_column(String(64))
    answers_sha256: Mapped[str] = mapped_column(String(64))
    # Big Five results only.
    archetype_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    archetypes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Interest results only: {"code", "ranking": [[area, count], ...], "boundary_ties", "empty"}.
    interest_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    quality_flags: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[AssessmentSession] = relationship(back_populates="result")
    trait_scores: Mapped[list["TraitScore"]] = relationship(
        back_populates="result", cascade="all, delete-orphan", order_by="TraitScore.position"
    )


class TraitScore(Base):
    __tablename__ = "personality_trait_scores"
    __table_args__ = (
        UniqueConstraint("result_id", "trait", name="uq_trait_per_result"),
        CheckConstraint("score is null or (score >= 0 and score <= 100)", name="ck_trait_score_range"),
        Index("ix_trait_scores_result", "result_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessment_results.id", ondelete="CASCADE"))
    trait: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    raw_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    band: Mapped[str | None] = mapped_column(String(16), nullable=True)
    answered: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)

    result: Mapped[AssessmentResult] = relationship(back_populates="trait_scores")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_type: Mapped[str] = mapped_column(String(64))
    subject_id: Mapped[str] = mapped_column(String(64))
    # Never put personal data or answers in details.
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CoachConversation(Base):
    """A coaching conversation. Message text lives encrypted in coach_messages."""

    __tablename__ = "coach_conversations"
    __table_args__ = (Index("ix_coach_conversations_user_updated", "user_id", "updated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_coach_conversations_user_id_users")
    )
    topic: Mapped[str] = mapped_column(String(32))
    # The assessment result the user allowed the coach to use. Cleared if the result is deleted.
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_results.id", ondelete="SET NULL", name="fk_coach_conversations_result_id"),
        nullable=True,
    )
    consent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_records.id", ondelete="RESTRICT", name="fk_coach_conversations_consent_id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["CoachMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CoachMessage.sequence",
        passive_deletes=True,
    )


class CoachMessage(Base):
    __tablename__ = "coach_messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_coach_message_sequence"),
        CheckConstraint("role in ('user','assistant')", name="ck_coach_message_role"),
        CheckConstraint(
            "kind in ('message','crisis_support','safety_replacement','unavailable')",
            name="ck_coach_message_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coach_conversations.id", ondelete="CASCADE", name="fk_coach_messages_conversation_id"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(32), default="message")
    # AES-GCM ciphertext (app.security.crypto). Never log or index this column.
    content_encrypted: Mapped[str] = mapped_column(Text)
    # Rule names only, never message text.
    safety_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[CoachConversation] = relationship(back_populates="messages")


class AiUsageRecord(Base):
    """One row per coach turn. Holds counts only, so it is kept for cost accounting after deletion."""

    __tablename__ = "ai_usage_records"
    __table_args__ = (Index("ix_ai_usage_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_ai_usage_records_user_id_users"), nullable=True
    )
    feature: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[str] = mapped_column(String(32))
    counts_toward_limit: Mapped[bool] = mapped_column(default=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


_RELATION_TYPE_CHECK = "relation_type in ('partner','friend','family','colleague')"


class RelationshipInvitation(Base):
    """A pending invitation to compare results. Only the token hash is stored; accepted or cancelled
    invitations are deleted, so nothing lingers once the link exists or the inviter changes their mind."""

    __tablename__ = "relationship_invitations"
    __table_args__ = (
        CheckConstraint(
            "relation_type in ('partner','friend','family','colleague')",
            name="ck_relationship_invitation_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    inviter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_relationship_invitations_inviter_id_users"),
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consent_records.id", ondelete="SET NULL", name="fk_relationship_invitations_consent_id"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RelationshipLink(Base):
    """Two people who both agreed to see a comparison of their Big Five results. Either person can
    revoke it, which deletes the row: the comparison is computed on request and never stored."""

    __tablename__ = "relationship_links"
    __table_args__ = (CheckConstraint(_RELATION_TYPE_CHECK, name="ck_relationship_link_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    inviter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_relationship_links_inviter_id_users"), index=True
    )
    invitee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_relationship_links_invitee_id_users"), index=True
    )
    # Both ids in sorted order, so one pair of people can have only one link.
    pair_key: Mapped[str] = mapped_column(String(80), unique=True)
    relation_type: Mapped[str] = mapped_column(String(16))
    inviter_consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "consent_records.id", ondelete="SET NULL", name="fk_relationship_links_inviter_consent_id"
        ),
        nullable=True,
    )
    invitee_consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "consent_records.id", ondelete="SET NULL", name="fk_relationship_links_invitee_consent_id"
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningActivityProgress(Base):
    """Which learning activities (leadership, emotional awareness) a user marked as done.

    Content ids only, never free text.
    """

    __tablename__ = "learning_activity_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "track", "module_id", "activity_id", name="uq_learning_activity_progress"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_learning_activity_progress_user_id_users"),
        index=True,
    )
    track: Mapped[str] = mapped_column(String(32))
    module_id: Mapped[str] = mapped_column(String(64))
    activity_id: Mapped[str] = mapped_column(String(64))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GrowthEnrollment(Base):
    """A user following a growth programme. Restarting resets the start time and progress."""

    __tablename__ = "growth_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "program_id", name="uq_growth_enrollment"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_growth_enrollments_user_id_users"), index=True
    )
    program_id: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GrowthDayProgress(Base):
    """A programme day marked done. Day numbers only, no free text."""

    __tablename__ = "growth_day_progress"
    __table_args__ = (UniqueConstraint("enrollment_id", "day", name="uq_growth_day_progress"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "growth_enrollments.id",
            ondelete="CASCADE",
            name="fk_growth_day_progress_enrollment_id_growth_enrollments",
        ),
        index=True,
    )
    day: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GrowthCheckIn(Base):
    """A weekly self-evaluation on a 1 to 5 scale. For the user's own reflection; never compared or ranked."""

    __tablename__ = "growth_check_ins"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "week", name="uq_growth_check_in"),
        CheckConstraint("rating between 1 and 5", name="ck_growth_check_in_rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "growth_enrollments.id",
            ondelete="CASCADE",
            name="fk_growth_check_ins_enrollment_id_growth_enrollments",
        ),
        index=True,
    )
    week: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalEntry(Base):
    """A private journal entry. Title, text and tags are encrypted with the row id as associated data.

    Only the kind, the optional 1 to 5 mood, the entry date and timestamps are stored in the clear.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "kind in ('daily','gratitude','goal','development','communication','free')",
            name="ck_journal_entry_kind",
        ),
        CheckConstraint("mood is null or mood between 1 and 5", name="ck_journal_entry_mood"),
        Index("ix_journal_entries_user_date", "user_id", "entry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_journal_entries_user_id_users")
    )
    kind: Mapped[str] = mapped_column(String(16))
    entry_date: Mapped[date] = mapped_column(Date)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_encrypted: Mapped[str] = mapped_column(Text)
    tags_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
