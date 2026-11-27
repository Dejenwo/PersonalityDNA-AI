"""goals and habits

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title_encrypted", sa.Text(), nullable=False),
        sa.Column("why_encrypted", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active','completed','archived')", name="ck_goal_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_goals_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("goals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_goals_user_id"), ["user_id"], unique=False)

    op.create_table(
        "goal_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("title_encrypted", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["goal_id"], ["goals.id"], name="fk_goal_milestones_goal_id_goals", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("goal_milestones", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_goal_milestones_goal_id"), ["goal_id"], unique=False)

    op.create_table(
        "habits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=True),
        sa.Column("title_encrypted", sa.Text(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("days between 1 and 127", name="ck_habit_days"),
        sa.ForeignKeyConstraint(
            ["goal_id"], ["goals.id"], name="fk_habits_goal_id_goals", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_habits_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("habits", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_habits_user_id"), ["user_id"], unique=False)

    op.create_table(
        "habit_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("habit_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["habit_id"], ["habits.id"], name="fk_habit_checks_habit_id_habits", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("habit_id", "day", name="uq_habit_check"),
    )
    with op.batch_alter_table("habit_checks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_habit_checks_habit_id"), ["habit_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("habit_checks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_habit_checks_habit_id"))

    op.drop_table("habit_checks")
    with op.batch_alter_table("habits", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_habits_user_id"))

    op.drop_table("habits")
    with op.batch_alter_table("goal_milestones", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_goal_milestones_goal_id"))

    op.drop_table("goal_milestones")
    with op.batch_alter_table("goals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_goals_user_id"))

    op.drop_table("goals")
