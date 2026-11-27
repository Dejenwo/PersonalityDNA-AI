"""growth infrastructure

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_event_counts",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=48), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("day", "name"),
    )
    op.create_table(
        "acquisitions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("referrer_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("medium", sa.String(length=64), nullable=True),
        sa.Column("campaign", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["referrer_id"], ["users.id"], name="fk_acquisitions_referrer_id_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_acquisitions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    with op.batch_alter_table("acquisitions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_acquisitions_referrer_id"), ["referrer_id"], unique=False)

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("in_app", sa.Boolean(), nullable=False),
        sa.Column("email", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notification_preferences_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kind", name="uq_notification_preferences_user_kind"),
    )
    with op.batch_alter_table("notification_preferences", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_notification_preferences_user_id"), ["user_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=300), nullable=True),
        sa.Column("dedupe_key", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.create_index("ix_notifications_user_created", ["user_id", "created_at"], unique=False)

    op.create_table(
        "referral_codes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_referral_codes_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("code"),
    )


def downgrade() -> None:
    op.drop_table("referral_codes")
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index("ix_notifications_user_created")

    op.drop_table("notifications")
    with op.batch_alter_table("notification_preferences", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notification_preferences_user_id"))

    op.drop_table("notification_preferences")
    with op.batch_alter_table("acquisitions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_acquisitions_referrer_id"))

    op.drop_table("acquisitions")
    op.drop_table("product_event_counts")
