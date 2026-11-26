"""ai coach

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("feature", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("counts_toward_limit", sa.Boolean(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ai_usage_records_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_usage_records", schema=None) as batch_op:
        batch_op.create_index("ix_ai_usage_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "coach_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=32), nullable=False),
        sa.Column("result_id", sa.Uuid(), nullable=True),
        sa.Column("consent_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["consent_records.id"],
            name="fk_coach_conversations_consent_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["assessment_results.id"],
            name="fk_coach_conversations_result_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_coach_conversations_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("coach_conversations", schema=None) as batch_op:
        batch_op.create_index("ix_coach_conversations_user_updated", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "coach_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content_encrypted", sa.Text(), nullable=False),
        sa.Column("safety_flags", sa.JSON(), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind in ('message','crisis_support','safety_replacement','unavailable')",
            name="ck_coach_message_kind",
        ),
        sa.CheckConstraint("role in ('user','assistant')", name="ck_coach_message_role"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["coach_conversations.id"],
            name="fk_coach_messages_conversation_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_coach_message_sequence"),
    )
    with op.batch_alter_table("coach_messages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_coach_messages_conversation_id"), ["conversation_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("coach_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_coach_messages_conversation_id"))

    op.drop_table("coach_messages")
    with op.batch_alter_table("coach_conversations", schema=None) as batch_op:
        batch_op.drop_index("ix_coach_conversations_user_updated")

    op.drop_table("coach_conversations")
    with op.batch_alter_table("ai_usage_records", schema=None) as batch_op:
        batch_op.drop_index("ix_ai_usage_user_created")

    op.drop_table("ai_usage_records")
