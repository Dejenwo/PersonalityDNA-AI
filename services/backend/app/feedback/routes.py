"""Feedback from people using the app, and the support triage list."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.admin.routes import need
from app.api.deps import client_ip, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser, OptionalUser
from app.database.models import User
from app.feedback.schemas import (
    AdminFeedback,
    AdminFeedbackList,
    FeedbackIn,
    FeedbackList,
    FeedbackOut,
    FeedbackStatusIn,
    Kind,
    Status,
)
from app.feedback.service import FeedbackService

router = APIRouter(tags=["feedback"], responses={404: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]


def get_feedback(request: Request) -> FeedbackService:
    svc: FeedbackService = request.app.state.feedback
    return svc


Svc = Annotated[FeedbackService, Depends(get_feedback)]


@router.post(
    "/api/v1/feedback",
    response_model=FeedbackOut,
    status_code=status.HTTP_201_CREATED,
    responses={429: {"model": ErrorResponse}},
)
def send_feedback(body: FeedbackIn, request: Request, db: Db, svc: Svc, user: OptionalUser) -> FeedbackOut:
    """Works signed in or out. Please don't include passwords or other people's details."""
    key = f"feedback:{user.id}" if user else f"feedback-ip:{client_ip(request)}"
    if not request.app.state.feedback_limiter.allow(key):
        raise ApiError(429, "rate_limited", "Thanks, we've had a lot from you. Please try again later.")
    return svc.submit(db, user, body)


@router.get("/api/v1/feedback", response_model=FeedbackList, responses={401: {"model": ErrorResponse}})
def my_feedback(db: Db, svc: Svc, user: CurrentUser) -> FeedbackList:
    """What you've sent while signed in, with its status."""
    return FeedbackList(items=svc.mine(db, user))


@router.get(
    "/api/v1/admin/feedback",
    response_model=AdminFeedbackList,
    tags=["admin"],
    responses={401: {"model": ErrorResponse}},
)
def triage_list(
    db: Db,
    svc: Svc,
    _: Annotated[User, Depends(need("feedback.read"))],
    status_filter: Annotated[Status | None, Query(alias="status")] = None,
    kind: Kind | None = None,
    before: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AdminFeedbackList:
    return svc.triage_list(db, status_filter, kind, before, limit)


@router.post(
    "/api/v1/admin/feedback/{feedback_id}/status",
    response_model=AdminFeedback,
    tags=["admin"],
    responses={401: {"model": ErrorResponse}},
)
def set_status(
    feedback_id: str,
    body: FeedbackStatusIn,
    db: Db,
    svc: Svc,
    admin: Annotated[User, Depends(need("feedback.manage"))],
) -> AdminFeedback:
    return svc.set_status(db, admin, feedback_id, body.status)
