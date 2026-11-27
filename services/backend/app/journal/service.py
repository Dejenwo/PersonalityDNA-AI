"""Private journal. Title, text and tags are encrypted at rest; search and tag counts run after decryption
on the server, scoped to the owner. Nothing here logs entry content."""

import base64
import json
import uuid
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.database.models import JournalEntry, User
from app.journal.schemas import EntryIn, EntryList, EntryOut, EntryPatch, SearchIn, TagCount
from app.security.crypto import FieldCipher

MAX_ENTRIES = 10_000
MAX_TAG_LENGTH = 32


def normalize_tags(tags: Iterable[str]) -> list[str]:
    """Lower case, trimmed, inner spaces collapsed, leading '#' dropped, duplicates removed, order kept."""
    out: list[str] = []
    for raw in tags:
        tag = " ".join(raw.strip().lstrip("#").lower().split())
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise ApiError(422, "invalid_tag", f"Tags can be at most {MAX_TAG_LENGTH} characters.")
        if tag not in out:
            out.append(tag)
    return out


def _check_date(d: date) -> date:
    # Allow one day ahead for time zones east of UTC.
    if d > datetime.now(UTC).date() + timedelta(days=1):
        raise ApiError(422, "future_date", "Journal entries can't be dated in the future.")
    return d


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        if not raw.startswith("o"):
            raise ValueError
        offset = int(raw[1:])
        if offset < 0:
            raise ValueError
        return offset
    except ValueError as exc:
        raise ApiError(422, "invalid_cursor", "The page cursor is not valid.") from exc


class JournalService:
    def __init__(self, cipher: FieldCipher) -> None:
        self.cipher = cipher

    # ---------- encryption ----------

    def _seal(self, e: JournalEntry, title: str | None, body: str, tags: list[str]) -> None:
        rid = str(e.id)
        e.title_encrypted = self.cipher.encrypt(title, f"journal:{rid}:title") if title else None
        e.body_encrypted = self.cipher.encrypt(body, f"journal:{rid}:body")
        e.tags_encrypted = self.cipher.encrypt(json.dumps(tags), f"journal:{rid}:tags")

    def out(self, e: JournalEntry) -> EntryOut:
        rid = str(e.id)
        return EntryOut(
            id=rid,
            kind=e.kind,
            title=self.cipher.decrypt(e.title_encrypted, f"journal:{rid}:title")
            if e.title_encrypted
            else None,
            body=self.cipher.decrypt(e.body_encrypted, f"journal:{rid}:body"),
            mood=e.mood,
            tags=json.loads(self.cipher.decrypt(e.tags_encrypted, f"journal:{rid}:tags")),
            entry_date=e.entry_date,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )

    # ---------- queries ----------

    @staticmethod
    def _ordered(user: User) -> Select[JournalEntry]:
        return (
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc(), JournalEntry.id.desc())
        )

    def get(self, db: Session, user: User, entry_id: str) -> JournalEntry:
        try:
            uid = uuid.UUID(entry_id)
        except ValueError:
            raise ApiError(404, "not_found", "Entry not found.") from None
        e = db.get(JournalEntry, uid)
        if e is None or e.user_id != user.id:
            raise ApiError(404, "not_found", "Entry not found.")
        return e

    def page(self, db: Session, user: User, cursor: str | None, limit: int) -> EntryList:
        offset = decode_cursor(cursor)
        rows = list(db.scalars(self._ordered(user).offset(offset).limit(limit + 1)))
        more = len(rows) > limit
        return EntryList(
            items=[self.out(e) for e in rows[:limit]],
            next_cursor=encode_cursor(offset + limit) if more else None,
        )

    def all_entries(self, db: Session, user: User) -> list[EntryOut]:
        return [self.out(e) for e in db.scalars(self._ordered(user))]

    def search(self, db: Session, user: User, body: SearchIn) -> EntryList:
        stmt = self._ordered(user)
        if body.kind:
            stmt = stmt.where(JournalEntry.kind == body.kind)
        if body.date_from:
            stmt = stmt.where(JournalEntry.entry_date >= body.date_from)
        if body.date_to:
            stmt = stmt.where(JournalEntry.entry_date <= body.date_to)
        words = (body.q or "").casefold().split()
        tags = normalize_tags([body.tag]) if body.tag else []
        tag = tags[0] if tags else None
        matches: list[EntryOut] = []
        for e in db.scalars(stmt):
            entry = self.out(e)
            if tag and tag not in entry.tags:
                continue
            haystack = " ".join([entry.title or "", entry.body, *entry.tags]).casefold()
            if all(w in haystack for w in words):
                matches.append(entry)
        offset = decode_cursor(body.cursor)
        page = matches[offset : offset + body.limit]
        more = offset + body.limit < len(matches)
        return EntryList(items=page, next_cursor=encode_cursor(offset + body.limit) if more else None)

    def tags(self, db: Session, user: User) -> list[TagCount]:
        counts: Counter[str] = Counter()
        for e in db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id)):
            counts.update(json.loads(self.cipher.decrypt(e.tags_encrypted, f"journal:{e.id}:tags")))
        return [TagCount(tag=t, count=n) for t, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]

    # ---------- writes ----------

    def create(self, db: Session, user: User, body: EntryIn) -> EntryOut:
        count = db.scalar(
            select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user.id)
        )
        if (count or 0) >= MAX_ENTRIES:
            raise ApiError(409, "journal_full", f"Your journal has reached {MAX_ENTRIES} entries.")
        now = datetime.now(UTC)
        e = JournalEntry(
            id=uuid.uuid4(),
            user_id=user.id,
            kind=body.kind,
            entry_date=_check_date(body.entry_date or now.date()),
            mood=body.mood,
            created_at=now,
            updated_at=now,
        )
        self._seal(e, (body.title or "").strip() or None, body.body, normalize_tags(body.tags))
        db.add(e)
        db.commit()
        return self.out(e)

    def update(self, db: Session, user: User, entry_id: str, patch: EntryPatch) -> EntryOut:
        e = self.get(db, user, entry_id)
        current = self.out(e)
        sent = patch.model_fields_set
        if "kind" in sent and patch.kind is not None:
            e.kind = patch.kind
        if "mood" in sent:
            e.mood = patch.mood
        if "entry_date" in sent and patch.entry_date is not None:
            e.entry_date = _check_date(patch.entry_date)
        title = ((patch.title or "").strip() or None) if "title" in sent else current.title
        text = patch.body if "body" in sent and patch.body is not None else current.body
        tags = normalize_tags(patch.tags) if "tags" in sent and patch.tags is not None else current.tags
        self._seal(e, title, text, tags)
        e.updated_at = datetime.now(UTC)
        db.commit()
        return self.out(e)

    def delete(self, db: Session, user: User, entry_id: str) -> None:
        db.delete(self.get(db, user, entry_id))
        db.commit()

    def delete_all(self, db: Session, user: User) -> int:
        result = db.execute(delete(JournalEntry).where(JournalEntry.user_id == user.id))
        db.commit()
        return int(getattr(result, "rowcount", 0) or 0)


def to_markdown(entries: list[EntryOut], kind_labels: dict[str, str], mood_scale: list[str]) -> str:
    lines = ["# My PersonalityDNA journal", ""]
    if not entries:
        lines.append("No entries yet.")
    for e in entries:
        heading = e.title or kind_labels.get(e.kind, e.kind)
        lines += [f"## {e.entry_date.isoformat()}: {heading}", ""]
        meta = [kind_labels.get(e.kind, e.kind)]
        if e.mood:
            meta.append(f"mood: {mood_scale[e.mood - 1]}")
        if e.tags:
            meta.append("tags: " + ", ".join(e.tags))
        lines += [f"*{' · '.join(meta)}*", "", e.body.strip(), ""]
    return "\n".join(lines).rstrip() + "\n"
