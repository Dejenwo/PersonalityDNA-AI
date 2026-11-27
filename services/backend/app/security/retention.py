"""Deletes data once its purpose has ended (docs/PRIVACY_REQUIREMENTS.md, retention column).

Run daily with scripts/purge_expired.py. Each rule is a single DELETE, safe to repeat.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete
from sqlalchemy.orm import Session

from app.database.models import (
    AssessmentSession,
    AuditEvent,
    AuthToken,
    Feedback,
    Notification,
    OrgInvitation,
    RefreshToken,
    RelationshipInvitation,
)
from app.notifications.service import KEEP_DAYS

# Unfinished assessments nobody signed in to claim; answers go with them (ON DELETE CASCADE).
ANONYMOUS_UNFINISHED_DAYS = 30
# Emailed tokens stay a little after expiry so a late click gets "expired" rather than "invalid".
EMAIL_TOKEN_GRACE = timedelta(days=1)
# Security and lifecycle events (ids and event names only) are kept for a year for investigations.
AUDIT_DAYS = 365
# Feedback is kept a year so recurring problems can be spotted, then deleted.
FEEDBACK_DAYS = 365


def purge_expired(db: Session, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    rules = {
        "anonymous_unfinished_assessments": delete(AssessmentSession).where(
            AssessmentSession.user_id.is_(None),
            AssessmentSession.status.in_(("in_progress", "abandoned")),
            AssessmentSession.updated_at < now - timedelta(days=ANONYMOUS_UNFINISHED_DAYS),
        ),
        "email_tokens": delete(AuthToken).where(AuthToken.expires_at < now - EMAIL_TOKEN_GRACE),
        # Revoked tokens are kept until expiry so reuse of a stolen token is still detected.
        "refresh_tokens": delete(RefreshToken).where(RefreshToken.expires_at < now),
        "relationship_invitations": delete(RelationshipInvitation).where(
            RelationshipInvitation.expires_at < now
        ),
        "organisation_invitations": delete(OrgInvitation).where(OrgInvitation.expires_at < now),
        "audit_events": delete(AuditEvent).where(AuditEvent.created_at < now - timedelta(days=AUDIT_DAYS)),
        "feedback": delete(Feedback).where(Feedback.created_at < now - timedelta(days=FEEDBACK_DAYS)),
        "notifications": delete(Notification).where(
            Notification.created_at < now - timedelta(days=KEEP_DAYS)
        ),
    }
    counts = {name: cast("CursorResult[Any]", db.execute(stmt)).rowcount or 0 for name, stmt in rules.items()}
    db.commit()
    return counts
