"""Share cards: create from a report, list, revoke, and look up by link token."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.database.models import ShareCard, User
from app.reports.service import ReportService
from app.security.crypto import FieldCipher
from app.security.tokens import hash_token, new_token
from app.sharing.card import build_card
from app.sharing.schemas import Card, CreateCardIn, ShareCardList, ShareCardOut

MAX_CARDS = 10


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class ShareService:
    def __init__(self, cipher: FieldCipher) -> None:
        self.cipher = cipher
        self.reports = ReportService(cipher)

    def out(self, c: ShareCard) -> ShareCardOut:
        return ShareCardOut(
            id=str(c.id),
            report_id=str(c.report_id),
            token=self.cipher.decrypt(c.token_encrypted, f"share:{c.id}"),
            created_at=_utc(c.created_at),
            card=Card.model_validate(c.card),
        )

    def list(self, db: Session, user: User) -> ShareCardList:
        rows = db.scalars(
            select(ShareCard).where(ShareCard.user_id == user.id).order_by(ShareCard.created_at.desc())
        )
        return ShareCardList(cards=[self.out(c) for c in rows])

    def create(self, db: Session, user: User, data: CreateCardIn) -> ShareCardOut:
        report = self.reports.get(db, user, data.report_id)
        body = self.reports.body(report)
        if not data.include_traits and not (data.include_archetype and body.profile):
            raise ApiError(422, "empty_card", "Choose at least one thing to show on the card.")
        count = db.scalar(select(func.count()).select_from(ShareCard).where(ShareCard.user_id == user.id))
        if (count or 0) >= MAX_CARDS:
            raise ApiError(
                409, "too_many_cards", f"You can have up to {MAX_CARDS} shared cards. Stop sharing one first."
            )
        created_on = _utc(report.created_at).strftime("%-d %B %Y")
        card = build_card(body, created_on, data.include_archetype, data.include_traits)
        token = new_token()
        c = ShareCard(
            id=uuid.uuid4(),
            user_id=user.id,
            report_id=report.id,
            token_hash=hash_token(token),
            card=card.model_dump(mode="json"),
            created_at=datetime.now(UTC),
        )
        c.token_encrypted = self.cipher.encrypt(token, f"share:{c.id}")
        db.add(c)
        db.commit()
        return self.out(c)

    def revoke(self, db: Session, user: User, card_id: str) -> None:
        try:
            cid = uuid.UUID(card_id)
        except ValueError:
            raise ApiError(404, "not_found", "Card not found.") from None
        c = db.get(ShareCard, cid)
        if c is None or c.user_id != user.id:
            raise ApiError(404, "not_found", "Card not found.")
        db.delete(c)
        db.commit()


def public_card(db: Session, token: str) -> Card:
    """Unknown, revoked and malformed tokens all look the same."""
    if not token or len(token) > 128:
        raise ApiError(404, "not_found", "This card isn't available.")
    c = db.scalar(select(ShareCard).where(ShareCard.token_hash == hash_token(token)))
    if c is None:
        raise ApiError(404, "not_found", "This card isn't available.")
    return Card.model_validate(c.card)
