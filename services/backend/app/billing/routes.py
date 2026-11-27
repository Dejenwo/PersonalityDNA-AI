"""Plans, entitlements, checkout and provider webhooks."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser
from app.billing.schemas import BillingOut, CheckoutIn, PlansOut, RedirectOut
from app.billing.service import BillingService

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
Db = Annotated[Session, Depends(get_db)]
ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}
MAX_WEBHOOK_BYTES = 1_000_000


def get_billing(request: Request) -> BillingService:
    svc: BillingService = request.app.state.billing
    return svc


Billing = Annotated[BillingService, Depends(get_billing)]


async def _body(request: Request) -> bytes:
    body = await request.body()
    if len(body) > MAX_WEBHOOK_BYTES:
        raise ApiError(413, "payload_too_large", "Webhook body too large.")
    return body


@router.get("/plans", response_model=PlansOut)
def plans(svc: Billing) -> PlansOut:
    """Public. Prices are initial and may change."""
    return svc.plans_out()


@router.get("/me", response_model=BillingOut, responses=ERRORS)
def me(user: CurrentUser, db: Db, svc: Billing) -> BillingOut:
    return svc.me(db, user)


@router.post("/checkout", response_model=RedirectOut, responses=ERRORS)
def checkout(body: CheckoutIn, user: CurrentUser, db: Db, svc: Billing) -> RedirectOut:
    """Returns the payment page to send the browser to."""
    return RedirectOut(url=svc.checkout(db, user, body.plan_id))


@router.post("/manage", response_model=RedirectOut, responses=ERRORS)
def manage(user: CurrentUser, db: Db, svc: Billing) -> RedirectOut:
    """Returns where to change or cancel the subscription."""
    return RedirectOut(url=svc.manage(db, user))


@router.post("/restore", response_model=BillingOut, responses=ERRORS)
def restore(user: CurrentUser, db: Db, svc: Billing) -> BillingOut:
    return svc.restore(db, user)


@router.post("/webhooks/stripe", status_code=204, response_class=Response, include_in_schema=False)
async def stripe_webhook(
    request: Request, db: Db, svc: Billing, stripe_signature: Annotated[str | None, Header()] = None
) -> Response:
    svc.stripe_webhook(db, await _body(request), stripe_signature)
    return Response(status_code=204)


@router.post("/webhooks/revenuecat", status_code=204, response_class=Response, include_in_schema=False)
async def revenuecat_webhook(
    request: Request, db: Db, svc: Billing, authorization: Annotated[str | None, Header()] = None
) -> Response:
    svc.revenuecat_webhook(db, await _body(request), authorization)
    return Response(status_code=204)
