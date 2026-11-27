"""generalise leadership activity progress into learning tracks

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_activity_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track", sa.String(length=32), nullable=False),
        sa.Column("module_id", sa.String(length=64), nullable=False),
        sa.Column("activity_id", sa.String(length=64), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_learning_activity_progress_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "track", "module_id", "activity_id", name="uq_learning_activity_progress"
        ),
    )
    with op.batch_alter_table("learning_activity_progress", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_learning_activity_progress_user_id"), ["user_id"], unique=False)
    op.execute(
        "INSERT INTO learning_activity_progress (id, user_id, track, module_id, activity_id, completed_at) "
        "SELECT id, user_id, 'leadership', module_id, activity_id, completed_at "
        "FROM leadership_activity_progress"
    )
    with op.batch_alter_table("leadership_activity_progress", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_leadership_activity_progress_user_id"))
    op.drop_table("leadership_activity_progress")


def downgrade() -> None:
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
    # Progress on other tracks has nowhere to go in the old schema and is dropped.
    op.execute(
        "INSERT INTO leadership_activity_progress (id, user_id, module_id, activity_id, completed_at) "
        "SELECT id, user_id, module_id, activity_id, completed_at "
        "FROM learning_activity_progress WHERE track = 'leadership'"
    )
    with op.batch_alter_table("learning_activity_progress", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_learning_activity_progress_user_id"))
    op.drop_table("learning_activity_progress")
