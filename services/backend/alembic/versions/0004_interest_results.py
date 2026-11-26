"""interest results

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("assessment_results", schema=None) as batch_op:
        batch_op.add_column(sa.Column("interest_profile", sa.JSON(), nullable=True))
        batch_op.alter_column("archetype_version", existing_type=sa.VARCHAR(length=32), nullable=True)
        batch_op.alter_column("archetypes", existing_type=sa.JSON(), nullable=True)


def downgrade() -> None:
    # Interest results cannot exist in the old schema; downgrading removes them.
    op.execute("DELETE FROM assessment_results WHERE archetypes IS NULL")
    with op.batch_alter_table("assessment_results", schema=None) as batch_op:
        batch_op.alter_column("archetypes", existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column("archetype_version", existing_type=sa.VARCHAR(length=32), nullable=False)
        batch_op.drop_column("interest_profile")
