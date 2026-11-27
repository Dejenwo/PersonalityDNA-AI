"""journal

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=True),
        sa.Column("title_encrypted", sa.Text(), nullable=True),
        sa.Column("body_encrypted", sa.Text(), nullable=False),
        sa.Column("tags_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind in ('daily','gratitude','goal','development','communication','free')",
            name="ck_journal_entry_kind",
        ),
        sa.CheckConstraint("mood is null or mood between 1 and 5", name="ck_journal_entry_mood"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_journal_entries_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("journal_entries", schema=None) as batch_op:
        batch_op.create_index("ix_journal_entries_user_date", ["user_id", "entry_date"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("journal_entries", schema=None) as batch_op:
        batch_op.drop_index("ix_journal_entries_user_date")

    op.drop_table("journal_entries")
