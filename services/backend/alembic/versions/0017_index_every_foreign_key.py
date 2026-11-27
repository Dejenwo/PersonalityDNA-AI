"""index every foreign key

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("admin_roles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_admin_roles_granted_by"), ["granted_by"], unique=False)

    with op.batch_alter_table("billing_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_billing_events_user_id"), ["user_id"], unique=False)

    with op.batch_alter_table("coach_conversations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_coach_conversations_consent_id"), ["consent_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_coach_conversations_result_id"), ["result_id"], unique=False)

    with op.batch_alter_table("habits", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_habits_goal_id"), ["goal_id"], unique=False)

    with op.batch_alter_table("org_invitations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_org_invitations_created_by"), ["created_by"], unique=False)

    with op.batch_alter_table("org_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_org_members_consent_id"), ["consent_id"], unique=False)

    with op.batch_alter_table("org_programs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_org_programs_created_by"), ["created_by"], unique=False)

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_organizations_created_by"), ["created_by"], unique=False)

    with op.batch_alter_table("relationship_invitations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_relationship_invitations_consent_id"), ["consent_id"], unique=False
        )

    with op.batch_alter_table("relationship_links", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_relationship_links_invitee_consent_id"), ["invitee_consent_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_relationship_links_inviter_consent_id"), ["inviter_consent_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("relationship_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_relationship_links_inviter_consent_id"))
        batch_op.drop_index(batch_op.f("ix_relationship_links_invitee_consent_id"))

    with op.batch_alter_table("relationship_invitations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_relationship_invitations_consent_id"))

    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_organizations_created_by"))

    with op.batch_alter_table("org_programs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_programs_created_by"))

    with op.batch_alter_table("org_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_members_consent_id"))

    with op.batch_alter_table("org_invitations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_org_invitations_created_by"))

    with op.batch_alter_table("habits", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_habits_goal_id"))

    with op.batch_alter_table("coach_conversations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_coach_conversations_result_id"))
        batch_op.drop_index(batch_op.f("ix_coach_conversations_consent_id"))

    with op.batch_alter_table("billing_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_billing_events_user_id"))

    with op.batch_alter_table("admin_roles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_admin_roles_granted_by"))
