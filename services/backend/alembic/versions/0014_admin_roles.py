"""admin roles

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "role in ('support','analyst','content','security','superadmin')", name="ck_admin_roles_role"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["users.id"], name="fk_admin_roles_granted_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_admin_roles_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_admin_roles_user_role"),
    )
    with op.batch_alter_table("admin_roles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_admin_roles_user_id"), ["user_id"], unique=False)

    # Support can grant complimentary Premium ("manual" subscriptions).
    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_subscriptions_provider", type_="check")
        batch_op.create_check_constraint(
            "ck_subscriptions_provider", "provider in ('stripe','revenuecat','dev','manual')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM subscriptions WHERE provider = 'manual'")
    with op.batch_alter_table("subscriptions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_subscriptions_provider", type_="check")
        batch_op.create_check_constraint(
            "ck_subscriptions_provider", "provider in ('stripe','revenuecat','dev')"
        )

    with op.batch_alter_table("admin_roles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_admin_roles_user_id"))

    op.drop_table("admin_roles")
