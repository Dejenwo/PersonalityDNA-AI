"""Report library: generate from the latest results, list, read, render as PDF, delete."""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.schemas import ResultOut
from app.api.v1.presenters import result_out
from app.assessments.content import ContentBundle
from app.coaching.service import result_kind
from app.database.models import AssessmentResult, AssessmentSession, Report, User
from app.reports.builder import body_sha256, build_report
from app.reports.schemas import ReportBody, ReportList, ReportOut, ReportSummary
from app.security.crypto import FieldCipher

MAX_REPORTS = 50


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def latest_results(db: Session, bundle: ContentBundle, user: User) -> dict[str, ResultOut]:
    """The newest result of each kind for this account."""
    rows = db.scalars(
        select(AssessmentResult)
        .join(AssessmentSession, AssessmentResult.session_id == AssessmentSession.id)
        .where(AssessmentSession.user_id == user.id)
        .order_by(AssessmentResult.created_at.desc())
    )
    out: dict[str, ResultOut] = {}
    for r in rows:
        kind = result_kind(r)
        if kind not in out:
            out[kind] = result_out(bundle, r)
    return out


class ReportService:
    def __init__(self, cipher: FieldCipher) -> None:
        self.cipher = cipher

    def _body(self, r: Report) -> ReportBody:
        return ReportBody.model_validate_json(self.cipher.decrypt(r.body_encrypted, f"report:{r.id}"))

    def out(self, r: Report) -> ReportOut:
        return ReportOut(
            id=str(r.id), created_at=_utc(r.created_at), body=self._body(r), sha256=r.body_sha256
        )

    def get(self, db: Session, user: User, report_id: str) -> Report:
        try:
            rid = uuid.UUID(report_id)
        except ValueError:
            raise ApiError(404, "not_found", "Report not found.") from None
        r = db.get(Report, rid)
        if r is None or r.user_id != user.id:
            raise ApiError(404, "not_found", "Report not found.")
        return r

    def list(self, db: Session, user: User) -> ReportList:
        rows = db.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc()))
        return ReportList(
            reports=[
                ReportSummary(
                    id=str(r.id),
                    created_at=_utc(r.created_at),
                    report_version=r.report_version,
                    headline=r.headline,
                    kinds=r.kinds,
                )
                for r in rows
            ]
        )

    def create(self, db: Session, bundle: ContentBundle, user: User) -> ReportOut:
        results = latest_results(db, bundle, user)
        if "big_five" not in results:
            raise ApiError(
                409, "no_results", "Take a Big Five assessment with your account first, then create a report."
            )
        count = len(db.scalars(select(Report.id).where(Report.user_id == user.id)).all())
        if count >= MAX_REPORTS:
            raise ApiError(
                409, "too_many_reports", f"You can keep up to {MAX_REPORTS} reports. Delete one first."
            )
        body = build_report(bundle, results)
        r = Report(
            id=uuid.uuid4(),
            user_id=user.id,
            report_version=body.report_version,
            headline=body.profile.name if body.profile else "Personality report",
            kinds=[s.kind for s in body.sources],
            body_sha256=body_sha256(body),
            created_at=datetime.now(UTC),
        )
        r.body_encrypted = self.cipher.encrypt(json.dumps(body.model_dump(mode="json")), f"report:{r.id}")
        db.add(r)
        db.commit()
        return self.out(r)

    def body(self, r: Report) -> ReportBody:
        return self._body(r)

    def delete(self, db: Session, user: User, report_id: str) -> None:
        db.delete(self.get(db, user, report_id))
        db.commit()
