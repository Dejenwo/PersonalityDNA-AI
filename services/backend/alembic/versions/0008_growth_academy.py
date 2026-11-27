"""growth academy

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "growth_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_growth_enrollments_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "program_id", name="uq_growth_enrollment"),
    )
    with op.batch_alter_table("growth_enrollments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_growth_enrollments_user_id"), ["user_id"], unique=False)

    op.create_table(
        "growth_check_ins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating between 1 and 5", name="ck_growth_check_in_rating"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["growth_enrollments.id"],
            name="fk_growth_check_ins_enrollment_id_growth_enrollments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "week", name="uq_growth_check_in"),
    )
    with op.batch_alter_table("growth_check_ins", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_growth_check_ins_enrollment_id"), ["enrollment_id"], unique=False
        )

    op.create_table(
        "growth_day_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["growth_enrollments.id"],
            name="fk_growth_day_progress_enrollment_id_growth_enrollments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "day", name="uq_growth_day_progress"),
    )
    with op.batch_alter_table("growth_day_progress", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_growth_day_progress_enrollment_id"), ["enrollment_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("growth_day_progress", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_growth_day_progress_enrollment_id"))

    op.drop_table("growth_day_progress")
    with op.batch_alter_table("growth_check_ins", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_growth_check_ins_enrollment_id"))

    op.drop_table("growth_check_ins")
    with op.batch_alter_table("growth_enrollments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_growth_enrollments_user_id"))

    op.drop_table("growth_enrollments")
