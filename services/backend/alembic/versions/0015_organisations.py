"""organisations

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("licence", sa.String(length=16), nullable=False),
        sa.Column("seat_limit", sa.Integer(), nullable=False),
        sa.Column("licensed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("licence in ('pilot','licensed')", name="ck_organizations_licence"),
        sa.CheckConstraint("seat_limit >= 1", name="ck_organizations_seat_limit"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_organizations_created_by_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "org_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('admin','member')", name="ck_org_invitations_role"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_org_invitations_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name="fk_org_invitations_org_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("org_invitations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_org_invitations_org_id"), ["org_id"], unique=False)

    op.create_table(
        "org_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("share_aggregates", sa.Boolean(), nullable=False),
        sa.Column("consent_id", sa.Uuid(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('owner','admin','member')", name="ck_org_members_role"),
        sa.ForeignKeyConstraint(
            ["consent_id"], ["consent_records.id"], name="fk_org_members_consent_id", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_org_members_org_id_organizations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_org_members_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),
    )
    with op.batch_alter_table("org_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_org_members_org_id"), ["org_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_org_members_user_id"), ["user_id"], unique=False)

    op.create_table(
        "org_programs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("growth_program_id", sa.String(length=64), nullable=True),
        sa.Column("learning", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_org_programs_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], name="fk_org_programs_org_id_organizations", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("org_programs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_org_programs_org_id"), ["org_id"], unique=False)

    op.create_table(
        "org_program_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["org_programs.id"],
            name="fk_org_program_participants_program_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_org_program_participants_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "user_id", name="uq_org_program_participants"),
    )
    with op.batch_alter_table("org_program_participants", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_org_program_participants_program_id"), ["program_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_org_program_participants_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("org_program_participants", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_program_participants_user_id"))
        batch_op.drop_index(batch_op.f("ix_org_program_participants_program_id"))

    op.drop_table("org_program_participants")
    with op.batch_alter_table("org_programs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_programs_org_id"))

    op.drop_table("org_programs")
    with op.batch_alter_table("org_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_members_user_id"))
        batch_op.drop_index(batch_op.f("ix_org_members_org_id"))

    op.drop_table("org_members")
    with op.batch_alter_table("org_invitations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_invitations_org_id"))

    op.drop_table("org_invitations")
    op.drop_table("organizations")
