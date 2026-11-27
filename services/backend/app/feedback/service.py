"""Beta feedback: people send bug reports, ideas and comments; support staff triage them.

The message is encrypted at rest and bound to the row id. It is never logged. Anonymous senders are not
linked to anything; signed-in senders are shown to support only if they agreed to be contacted.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.database.models import Feedback, User
from app.feedback.schemas import AdminFeedback, AdminFeedbackList, FeedbackIn, FeedbackOut
from app.security.crypto import FieldCipher

STATUSES = ("new", "planned", "fixed", "closed")


def _context(fid: uuid.UUID) -> str:
    return f"feedback:{fid}"


class FeedbackService:
    def __init__(self, cipher: FieldCipher) -> None:
        self.cipher = cipher

    def _out(self, f: Feedback) -> FeedbackOut:
        return FeedbackOut(
            id=str(f.id),
            kind=f.kind,
            message=self.cipher.decrypt(f.message_encrypted, _context(f.id)),
            page=f.page,
            status=f.status,
            created_at=f.created_at,
        )

    def submit(self, db: Session, user: User | None, body: FeedbackIn) -> FeedbackOut:
        fid = uuid.uuid4()
        f = Feedback(
            id=fid,
            user_id=user.id if user else None,
            kind=body.kind,
            message_encrypted=self.cipher.encrypt(body.message, _context(fid)),
            page=body.page,
            app_version=body.app_version,
            contact_ok=bool(user and body.contact_ok),
            status="new",
        )
        db.add(f)
        db.commit()
        db.refresh(f)
        return self._out(f)

    def mine(self, db: Session, user: User, limit: int | None = 50) -> list[FeedbackOut]:
        stmt = select(Feedback).where(Feedback.user_id == user.id).order_by(Feedback.created_at.desc())
        rows = db.scalars(stmt.limit(limit) if limit else stmt)
        return [self._out(f) for f in rows]

    # ---------- support ----------

    def _admin_out(self, f: Feedback) -> AdminFeedback:
        base = self._out(f)
        return AdminFeedback(
            **base.model_dump(),
            app_version=f.app_version,
            signed_in=f.user_id is not None,
            user_id=str(f.user_id) if f.user_id and f.contact_ok else None,
            updated_at=f.updated_at,
        )

    def triage_list(
        self, db: Session, status: str | None, kind: str | None, before: datetime | None, limit: int
    ) -> AdminFeedbackList:
        stmt = select(Feedback).order_by(Feedback.created_at.desc(), Feedback.id).limit(limit + 1)
        if status:
            stmt = stmt.where(Feedback.status == status)
        if kind:
            stmt = stmt.where(Feedback.kind == kind)
        if before is not None:
            stmt = stmt.where(Feedback.created_at < before)
        rows = list(db.scalars(stmt))
        more = len(rows) > limit
        rows = rows[:limit]
        counts = {s: 0 for s in STATUSES}
        for s, n in db.execute(select(Feedback.status, func.count()).group_by(Feedback.status)):
            counts[s] = n
        return AdminFeedbackList(
            items=[self._admin_out(f) for f in rows],
            counts=counts,
            next_before=rows[-1].created_at if more and rows else None,
        )

    def set_status(self, db: Session, admin: User, feedback_id: str, status: str) -> AdminFeedback:
        from app.admin.service import audit  # local import: admin imports many domains

        try:
            fid = uuid.UUID(feedback_id)
        except ValueError:
            raise ApiError(404, "not_found", "Not found.") from None
        f = db.get(Feedback, fid)
        if f is None:
            raise ApiError(404, "not_found", "Not found.")
        if f.status != status:
            audit(db, admin, "admin.feedback_status", str(f.id), old=f.status, new=status)
            f.status = status
            f.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(f)
        return self._admin_out(f)
