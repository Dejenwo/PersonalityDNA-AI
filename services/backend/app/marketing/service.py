"""Referral links, first-touch attribution and privacy-preserving product event counts.

Referrers see counts only, never who joined. Product events are daily counters by name: no user id, IP
address, cookie or free text is stored, so they need no tracking consent.
"""

import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Acquisition, ProductEventCount, ReferralCode, User

ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o, 1/l/i
EVENTS = frozenset(
    {
        "landing_view",
        "pricing_view",
        "assessment_intro_view",
        "big_five_article_view",
        "referral_landing",
        "share_card_view",
        "organisations_view",
    }
)
REFERRAL_NOTE = (
    "You see how many people joined with your link, never who they are. "
    "There are no rewards for referrals at the moment."
)


def _now() -> datetime:
    return datetime.now(UTC)


def referral_code(db: Session, user: User) -> str:
    row = db.get(ReferralCode, user.id)
    if row is None:
        while True:
            code = "".join(secrets.choice(ALPHABET) for _ in range(8))
            if db.scalar(select(ReferralCode.user_id).where(ReferralCode.code == code)) is None:
                break
        row = ReferralCode(user_id=user.id, code=code, created_at=_now())
        db.add(row)
        db.commit()
    return row.code


def referral_joins(db: Session, user: User) -> int:
    """Verified accounts that joined with the person's link. Whether any of them pay is never shown to the
    referrer: with small numbers it would reveal a named friend's billing."""
    joined = db.scalar(
        select(func.count())
        .select_from(Acquisition)
        .join(User, User.id == Acquisition.user_id)
        .where(Acquisition.referrer_id == user.id, User.email_verified_at.is_not(None))
    )
    return joined or 0


def record_acquisition(
    db: Session,
    user_id: uuid.UUID,
    referral: str | None,
    source: str | None,
    medium: str | None,
    campaign: str | None,
) -> None:
    """First touch for a new account. An unknown referral code is ignored rather than rejected."""
    referrer = None
    if referral:
        referrer = db.scalar(select(ReferralCode.user_id).where(ReferralCode.code == referral.lower()))
    if referrer is None and not (source or medium or campaign):
        return
    db.add(
        Acquisition(
            user_id=user_id,
            referrer_id=referrer if referrer != user_id else None,
            source=source,
            medium=medium,
            campaign=campaign,
            created_at=_now(),
        )
    )


def count_event(db: Session, name: str, day: date | None = None) -> None:
    day = day or _now().date()
    row = db.get(ProductEventCount, (day, name))
    if row is None:
        db.add(ProductEventCount(day=day, name=name, count=1))
    else:
        row.count += 1
    db.commit()


def event_totals(db: Session, days: int = 30) -> dict[str, int]:
    since = _now().date() - timedelta(days=days - 1)
    rows = db.execute(
        select(ProductEventCount.name, func.sum(ProductEventCount.count))
        .where(ProductEventCount.day >= since)
        .group_by(ProductEventCount.name)
    ).all()
    return {name: int(total or 0) for name, total in rows}


def acquisition_summary(db: Session, days: int = 30) -> tuple[int, dict[str, int]]:
    """(referred sign-ups, sign-ups by source) for accounts created in the window."""
    since = _now() - timedelta(days=days)
    base = select(Acquisition).join(User, User.id == Acquisition.user_id).where(User.created_at >= since)
    referred = db.scalar(
        select(func.count()).select_from(base.where(Acquisition.referrer_id.is_not(None)).subquery())
    )
    by_source = db.execute(
        select(Acquisition.source, func.count())
        .join(User, User.id == Acquisition.user_id)
        .where(User.created_at >= since, Acquisition.source.is_not(None))
        .group_by(Acquisition.source)
    ).all()
    return referred or 0, {str(s): int(n) for s, n in by_source}
