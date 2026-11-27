"""share cards

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "share_cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("card", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"], name="fk_share_cards_report_id_reports", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_share_cards_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("share_cards", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_share_cards_report_id"), ["report_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_share_cards_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("share_cards", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_share_cards_user_id"))
        batch_op.drop_index(batch_op.f("ix_share_cards_report_id"))

    op.drop_table("share_cards")
