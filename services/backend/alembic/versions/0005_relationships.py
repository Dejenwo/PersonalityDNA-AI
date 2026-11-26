"""relationships

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "relationship_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inviter_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("consent_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "relation_type in ('partner','friend','family','colleague')",
            name="ck_relationship_invitation_type",
        ),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["consent_records.id"],
            name="fk_relationship_invitations_consent_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["inviter_id"],
            ["users.id"],
            name="fk_relationship_invitations_inviter_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("relationship_invitations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_relationship_invitations_inviter_id"), ["inviter_id"], unique=False
        )

    op.create_table(
        "relationship_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inviter_id", sa.Uuid(), nullable=False),
        sa.Column("invitee_id", sa.Uuid(), nullable=False),
        sa.Column("pair_key", sa.String(length=80), nullable=False),
        sa.Column("relation_type", sa.String(length=16), nullable=False),
        sa.Column("inviter_consent_id", sa.Uuid(), nullable=True),
        sa.Column("invitee_consent_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "relation_type in ('partner','friend','family','colleague')", name="ck_relationship_link_type"
        ),
        sa.ForeignKeyConstraint(
            ["invitee_consent_id"],
            ["consent_records.id"],
            name="fk_relationship_links_invitee_consent_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["invitee_id"], ["users.id"], name="fk_relationship_links_invitee_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inviter_consent_id"],
            ["consent_records.id"],
            name="fk_relationship_links_inviter_consent_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["inviter_id"], ["users.id"], name="fk_relationship_links_inviter_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair_key"),
    )
    with op.batch_alter_table("relationship_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_relationship_links_invitee_id"), ["invitee_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_relationship_links_inviter_id"), ["inviter_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("relationship_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_relationship_links_inviter_id"))
        batch_op.drop_index(batch_op.f("ix_relationship_links_invitee_id"))

    op.drop_table("relationship_links")
    with op.batch_alter_table("relationship_invitations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_relationship_invitations_inviter_id"))

    op.drop_table("relationship_invitations")
