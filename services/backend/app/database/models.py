"""ORM models for the assessment vertical slice.

Tables for later phases (profiles, coaching, growth, subscriptions...) are designed in
docs/DATABASE_DESIGN.md and will be added with their own migrations.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
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
    archetype_version: Mapped[str] = mapped_column(String(32))
    archetypes: Mapped[dict[str, Any]] = mapped_column(JSON)
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
