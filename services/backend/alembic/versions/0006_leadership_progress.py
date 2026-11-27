"""leadership progress

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leadership_activity_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.String(length=64), nullable=False),
        sa.Column("activity_id", sa.String(length=64), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_leadership_activity_progress_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "module_id", "activity_id", name="uq_leadership_activity_progress"),
    )
    with op.batch_alter_table("leadership_activity_progress", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_leadership_activity_progress_user_id"), ["user_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("leadership_activity_progress", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_leadership_activity_progress_user_id"))

    op.drop_table("leadership_activity_progress")
