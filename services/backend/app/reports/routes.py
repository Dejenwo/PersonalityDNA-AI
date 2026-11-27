"""Personality reports. Signed-in users only; reports belong to their owner (others get 404)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.reports.pdf import render_pdf
from app.reports.schemas import ReportList, ReportOut
from app.reports.service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"], responses={401: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse}}


def get_reports(request: Request) -> ReportService:
    return ReportService(request.app.state.cipher)


Reports = Annotated[ReportService, Depends(get_reports)]


@router.get("", response_model=ReportList)
def list_reports(user: CurrentUser, db: Db, svc: Reports) -> ReportList:
    return svc.list(db, user)


@router.post(
    "",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def create_report(user: CurrentUser, db: Db, svc: Reports, content: Content) -> ReportOut:
    """Builds a new report from your latest Big Five, interest and leadership results."""
    return svc.create(db, content, user)


@router.get("/{report_id}", response_model=ReportOut, responses=NOT_FOUND)
def get_report(report_id: str, user: CurrentUser, db: Db, svc: Reports) -> ReportOut:
    return svc.out(svc.get(db, user, report_id))


@router.get(
    "/{report_id}/pdf",
    response_class=Response,
    responses={**NOT_FOUND, 200: {"content": {"application/pdf": {}}}},
)
def report_pdf(report_id: str, user: CurrentUser, db: Db, svc: Reports) -> Response:
    r = svc.get(db, user, report_id)
    pdf = render_pdf(svc.body(r), r.created_at.strftime("%-d %B %Y"))
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="personality-report-{r.created_at:%Y-%m-%d}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.delete(
    "/{report_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, responses=NOT_FOUND
)
def delete_report(report_id: str, user: CurrentUser, db: Db, svc: Reports) -> Response:
    svc.delete(db, user, report_id)
    return Response(status_code=204)
