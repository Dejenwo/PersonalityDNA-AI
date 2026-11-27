"""Share cards. Owners create and revoke them; anyone with the link can read the card (no sign-in)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import ErrorResponse
from app.auth.deps import CurrentUser
from app.sharing.card import render_svg
from app.sharing.schemas import Card, CreateCardIn, ShareCardList, ShareCardOut
from app.sharing.service import ShareService, public_card

router = APIRouter(prefix="/api/v1/share-cards", tags=["sharing"], responses={401: {"model": ErrorResponse}})
public_router = APIRouter(prefix="/api/v1/public/cards", tags=["sharing"])
Db = Annotated[Session, Depends(get_db)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse}}
# Revocation must take effect at once, and cards should not be indexed by search engines.
PUBLIC_HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
SVG_CSP = "default-src 'none'; style-src 'unsafe-inline'"


def get_share(request: Request) -> ShareService:
    return ShareService(request.app.state.cipher)


Share = Annotated[ShareService, Depends(get_share)]


@router.get("", response_model=ShareCardList)
def list_cards(user: CurrentUser, db: Db, svc: Share) -> ShareCardList:
    return svc.list(db, user)


@router.post(
    "",
    response_model=ShareCardOut,
    status_code=status.HTTP_201_CREATED,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_card(data: CreateCardIn, user: CurrentUser, db: Db, svc: Share) -> ShareCardOut:
    """Publishes a card from one of your reports. Anyone with the link can see it until you stop sharing."""
    return svc.create(db, user, data)


@router.delete(
    "/{card_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, responses=NOT_FOUND
)
def revoke_card(card_id: str, user: CurrentUser, db: Db, svc: Share) -> Response:
    svc.revoke(db, user, card_id)
    return Response(status_code=204)


@public_router.get("/{token}", response_model=Card, responses=NOT_FOUND)
def read_card(token: str, db: Db, response: Response) -> Card:
    response.headers.update(PUBLIC_HEADERS)
    return public_card(db, token)


@public_router.get(
    "/{token}/image.svg",
    response_class=Response,
    responses={**NOT_FOUND, 200: {"content": {"image/svg+xml": {}}}},
)
def card_image(token: str, db: Db) -> Response:
    svg = render_svg(public_card(db, token))
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={**PUBLIC_HEADERS, "Content-Security-Policy": SVG_CSP},
    )
