"""Referral link for the signed-in person, and anonymous product event counts."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_db
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser
from app.marketing import service
from app.marketing.service import REFERRAL_NOTE

router = APIRouter(tags=["growth"])
Db = Annotated[Session, Depends(get_db)]


class ReferralOut(BaseModel):
    code: str
    link: str
    joined: int
    note: str


class EventIn(BaseModel):
    name: str


@router.get("/api/v1/referrals/me", response_model=ReferralOut, responses={401: {"model": ErrorResponse}})
def my_referral(request: Request, user: CurrentUser, db: Db) -> ReferralOut:
    code = service.referral_code(db, user)
    joined = service.referral_joins(db, user)
    base = request.app.state.settings.web_base_url.rstrip("/")
    return ReferralOut(
        code=code,
        link=f"{base}/?ref={code}",
        joined=joined,
        note=REFERRAL_NOTE,
    )


@router.post("/api/v1/analytics/events", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def count_event(body: EventIn, request: Request, db: Db) -> Response:
    """Adds one to today's count for a known event name. Unknown names and rate-limited calls are ignored, so
    the endpoint never reveals anything and never fails the page."""
    limiter = request.app.state.events_limiter
    if body.name in service.EVENTS and limiter.allow(f"events:{client_ip(request)}"):
        service.count_event(db, body.name)
    return Response(status_code=204)
