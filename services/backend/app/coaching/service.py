"""Coach orchestration: authorization, consent, context, limits, safety, streaming and persistence.

One provider call per turn (docs/AI_ARCHITECTURE.md). Message text is encrypted at rest and never
logged; usage records and audit events hold counts and rule names only.
"""

import json
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.assessments import service as assessments
from app.assessments.content import ContentBundle
from app.coaching.context import TOPICS, facts_from_result, render_context
from app.coaching.prompts import PromptTemplate
from app.coaching.providers import CoachRequest, Completion, LLMProvider, ProviderError, Turn
from app.coaching.safety import (
    CRISIS_RESPONSE,
    REFUSAL_REPLACEMENT,
    SAFETY_REPLACEMENT,
    blocked_output,
    grounding_flags,
    screen_input,
)
from app.coaching.schemas import (
    CoachMessageOut,
    CoachStatus,
    ConversationOut,
    ConversationSummary,
    CreateConversationIn,
)
from app.core.config import Settings
from app.database.models import (
    AiUsageRecord,
    AssessmentResult,
    AssessmentSession,
    AuditEvent,
    CoachConversation,
    CoachMessage,
    ConsentRecord,
    User,
)
from app.security.consent import COACH_CONSENT_TYPE, COACH_POLICY_VERSION
from app.security.crypto import FieldCipher

FEATURE = "coach"
WINDOW = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, separators=(',', ':'))}\n\n"


@dataclass(frozen=True)
class PreparedTurn:
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    text: str
    input_flags: list[str]
    request: CoachRequest


class CoachService:
    def __init__(
        self,
        settings: Settings,
        provider: LLMProvider,
        cipher: FieldCipher,
        prompt: PromptTemplate,
        sessionmaker: Callable[[], Session],
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.cipher = cipher
        self.prompt = prompt
        self._sessionmaker = sessionmaker
        self._inflight: dict[uuid.UUID, float] = {}
        self._lock = threading.Lock()

    # ---------- availability, consent and limits ----------

    def require_enabled(self) -> None:
        if not self.settings.coach_enabled:
            raise ApiError(503, "coach_unavailable", "The coach is not available right now.")

    def usage(
        self, db: Session, user_id: uuid.UUID, now: datetime | None = None
    ) -> tuple[int, datetime | None]:
        """(messages counted in the rolling window, when the next one frees up if at the limit)."""
        now = now or _now()
        rows = db.scalars(
            select(AiUsageRecord.created_at)
            .where(
                AiUsageRecord.user_id == user_id,
                AiUsageRecord.counts_toward_limit.is_(True),
                AiUsageRecord.created_at > now - WINDOW,
            )
            .order_by(AiUsageRecord.created_at)
        ).all()
        used = len(rows)
        limit = self.settings.coach_daily_message_limit
        resets_at = None
        if used >= limit and rows:
            resets_at = _aware(rows[used - limit]) + WINDOW
        return used, resets_at

    def status(self, db: Session, user: User) -> CoachStatus:
        used, resets_at = self.usage(db, user.id)
        limit = self.settings.coach_daily_message_limit
        return CoachStatus(
            enabled=self.settings.coach_enabled,
            demo_mode=self.provider.name == "mock",
            email_verified=user.email_verified_at is not None,
            consent_policy_version=COACH_POLICY_VERSION,
            daily_limit=limit,
            used=used,
            remaining=max(0, limit - used),
            resets_at=resets_at,
            has_results=self._latest_result(db, user.id) is not None,
        )

    def _consent(self, db: Session, user_id: uuid.UUID, policy_version: str) -> ConsentRecord:
        if policy_version != COACH_POLICY_VERSION:
            raise ApiError(
                409,
                "consent_outdated",
                "The coaching terms have changed. Please review them again.",
                {"policy_version": COACH_POLICY_VERSION},
            )
        existing = db.scalar(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == COACH_CONSENT_TYPE,
                ConsentRecord.policy_version == policy_version,
                ConsentRecord.granted.is_(True),
            )
        )
        if existing:
            return existing
        record = ConsentRecord(
            user_id=user_id,
            consent_type=COACH_CONSENT_TYPE,
            policy_version=policy_version,
            granted=True,
            age_confirmed_18_plus=True,  # accounts require 18+ at registration
        )
        db.add(record)
        db.flush()
        return record

    # ---------- conversations ----------

    def _latest_result(
        self, db: Session, user_id: uuid.UUID, kind: str | None = None
    ) -> AssessmentResult | None:
        query = (
            select(AssessmentResult)
            .join(AssessmentSession, AssessmentResult.session_id == AssessmentSession.id)
            .where(AssessmentSession.user_id == user_id)
        )
        if kind == "big_five":
            query = query.where(AssessmentResult.archetype_version.is_not(None))
        elif kind == "interests":
            query = query.where(AssessmentResult.interest_profile.is_not(None))
        elif kind == "leadership":
            query = query.where(
                AssessmentResult.archetype_version.is_(None), AssessmentResult.interest_profile.is_(None)
            )
        return db.scalar(query.order_by(AssessmentResult.created_at.desc()).limit(1))

    def _context_results(
        self, db: Session, conv: CoachConversation
    ) -> tuple[AssessmentResult | None, AssessmentResult | None, AssessmentResult | None]:
        """(Big Five, interests, leadership) results the coach may use: the chosen result plus the latest
        of each other kind. All None unless the user shared results."""
        if conv.result_id is None:
            return None, None, None
        chosen = db.get(AssessmentResult, conv.result_id)
        if chosen is None:
            return None, None, None
        kinds = ("big_five", "interests", "leadership")
        found = {
            k: chosen if result_kind(chosen) == k else self._latest_result(db, conv.user_id, k) for k in kinds
        }
        return found["big_five"], found["interests"], found["leadership"]

    def create_conversation(self, db: Session, user: User, body: CreateConversationIn) -> CoachConversation:
        consent = self._consent(db, user.id, body.consent.policy_version)
        result_id = None
        if body.use_results:
            if body.result_id is not None:
                result_id = assessments.get_authorized_result(db, body.result_id, None, user.id).id
            else:
                latest = self._latest_result(db, user.id)
                result_id = latest.id if latest else None
        now = _now()
        conv = CoachConversation(
            user_id=user.id,
            topic=body.topic,
            result_id=result_id,
            consent_id=consent.id,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.commit()
        return conv

    def list_conversations(self, db: Session, user_id: uuid.UUID) -> list[ConversationSummary]:
        counts = (
            select(CoachMessage.conversation_id, func.count().label("n"))
            .group_by(CoachMessage.conversation_id)
            .subquery()
        )
        rows = db.execute(
            select(CoachConversation, func.coalesce(counts.c.n, 0))
            .outerjoin(counts, counts.c.conversation_id == CoachConversation.id)
            .where(CoachConversation.user_id == user_id)
            .order_by(CoachConversation.updated_at.desc())
        ).all()
        return [self._summary(conv, int(n)) for conv, n in rows]

    def get_conversation(
        self, db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> CoachConversation:
        conv = db.get(CoachConversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            raise ApiError(404, "not_found", "Conversation not found.")
        return conv

    def delete_conversation(self, db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        conv = self.get_conversation(db, user_id, conversation_id)
        if self._busy(conv.id):
            raise ApiError(409, "coach_busy", "Please wait for the current reply to finish.")
        db.delete(conv)
        db.commit()

    def _summary(self, conv: CoachConversation, count: int) -> ConversationSummary:
        return ConversationSummary(
            id=conv.id,
            topic=conv.topic,
            title=TOPICS.get(conv.topic, TOPICS["general"])[0],
            uses_results=conv.result_id is not None,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count,
        )

    def message_out(self, msg: CoachMessage) -> CoachMessageOut:
        return CoachMessageOut(
            id=msg.id,
            role=msg.role,
            kind=msg.kind,
            content=self.cipher.decrypt(msg.content_encrypted, str(msg.id)),
            created_at=msg.created_at,
        )

    def conversation_out(self, conv: CoachConversation) -> ConversationOut:
        summary = self._summary(conv, len(conv.messages))
        return ConversationOut(**summary.model_dump(), messages=[self.message_out(m) for m in conv.messages])

    # ---------- turns ----------

    def _busy(self, conversation_id: uuid.UUID) -> bool:
        started = self._inflight.get(conversation_id)
        # An entry older than the provider timeout belongs to a stream that never ran; ignore it.
        return (
            started is not None
            and time.monotonic() - started < self.settings.coach_request_timeout_seconds + 30
        )

    def _acquire(self, conversation_id: uuid.UUID) -> None:
        with self._lock:
            if self._busy(conversation_id):
                raise ApiError(409, "coach_busy", "Please wait for the current reply to finish.")
            self._inflight[conversation_id] = time.monotonic()

    def _release(self, conversation_id: uuid.UUID) -> None:
        with self._lock:
            self._inflight.pop(conversation_id, None)

    def _history(self, conv: CoachConversation) -> list[Turn]:
        msgs = list(conv.messages)
        turns: list[Turn] = []
        for i, m in enumerate(msgs):
            nxt = msgs[i + 1] if i + 1 < len(msgs) else None
            # Crisis exchanges were handled without the model and are not sent to it (minimization).
            if m.kind == "crisis_support" or (nxt is not None and nxt.kind == "crisis_support"):
                continue
            text = self.cipher.decrypt(m.content_encrypted, str(m.id))
            turns.append(Turn(role=m.role, content=text))  # type: ignore[arg-type]
        keep = self.settings.coach_history_messages
        return turns[-keep:] if keep else []

    @staticmethod
    def _merge(turns: list[Turn]) -> list[Turn]:
        """The first turn must be the user's and roles must alternate."""
        merged: list[Turn] = []
        for t in turns:
            if not merged and t.role != "user":
                continue
            if merged and merged[-1].role == t.role:
                merged[-1] = Turn(role=t.role, content=merged[-1].content + "\n\n" + t.content)
            else:
                merged.append(t)
        return merged

    def start_turn(
        self, db: Session, bundle: ContentBundle, conv: CoachConversation, text: str
    ) -> Iterator[str]:
        text = text.strip()
        if not text:
            raise ApiError(422, "validation_error", "Please write a message.")
        screen = screen_input(text)
        self._acquire(conv.id)
        try:
            if screen.crisis:
                # Never blocked by limits and never sent to the model.
                return self._crisis_turn(db, conv, text, screen.flags, screen.crisis)
            used, resets_at = self.usage(db, conv.user_id)
            if used >= self.settings.coach_daily_message_limit:
                raise ApiError(
                    429,
                    "coach_limit_reached",
                    "You've reached today's coaching limit.",
                    {"resets_at": resets_at.isoformat() if resets_at else None},
                )
            result, interests, leadership = self._context_results(db, conv)
            facts = facts_from_result(
                bundle,
                result,
                conv.topic,
                interests=interests,
                leadership=leadership,
                crisis_support_shown=any(m.kind == "crisis_support" for m in conv.messages),
            )
            turns = self._merge([*self._history(conv), Turn(role="user", content=text)])
            prepared = PreparedTurn(
                conversation_id=conv.id,
                user_id=conv.user_id,
                text=text,
                input_flags=screen.flags,
                request=CoachRequest(
                    system_instructions=self.prompt.text,
                    system_context=render_context(facts),
                    turns=turns,
                    max_tokens=self.settings.coach_max_output_tokens,
                    facts=facts,
                ),
            )
        except BaseException:
            self._release(conv.id)
            raise
        return self._stream(prepared)

    def _crisis_turn(
        self, db: Session, conv: CoachConversation, text: str, flags: list[str], category: str
    ) -> Iterator[str]:
        try:
            user_msg, reply = self._persist(db, conv.id, text, flags, CRISIS_RESPONSE, "crisis_support", [])
            db.add(
                AuditEvent(
                    event_type="coach.crisis_support",
                    subject_type="coach_conversation",
                    subject_id=str(conv.id),
                    details={"category": category},
                )
            )
            self._record(db, conv.user_id, "rules", "none", "crisis_support", counts=False)
            db.commit()
        finally:
            self._release(conv.id)
        events = [
            sse("start", {"conversation_id": str(conv.id)}),
            sse("delta", {"text": CRISIS_RESPONSE}),
            sse("done", self._done(db, conv.user_id, user_msg, reply)),
        ]
        return iter(events)

    def _done(
        self, db: Session, user_id: uuid.UUID, user_msg: CoachMessage, reply: CoachMessage
    ) -> dict[str, Any]:
        used, _ = self.usage(db, user_id)
        return {
            "user_message": self.message_out(user_msg).model_dump(mode="json"),
            "assistant_message": self.message_out(reply).model_dump(mode="json"),
            "remaining": max(0, self.settings.coach_daily_message_limit - used),
        }

    def _persist(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user_text: str,
        user_flags: list[str],
        reply_text: str,
        reply_kind: str,
        reply_flags: list[str],
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> tuple[CoachMessage, CoachMessage]:
        now = _now()
        last = db.scalar(
            select(func.max(CoachMessage.sequence)).where(CoachMessage.conversation_id == conversation_id)
        )
        seq = (last or 0) + 1
        user_msg = CoachMessage(
            id=uuid.uuid4(), conversation_id=conversation_id, sequence=seq, role="user", kind="message",
            safety_flags=user_flags, created_at=now,
        )  # fmt: skip
        user_msg.content_encrypted = self.cipher.encrypt(user_text, str(user_msg.id))
        reply = CoachMessage(
            id=uuid.uuid4(), conversation_id=conversation_id, sequence=seq + 1, role="assistant",
            kind=reply_kind, safety_flags=reply_flags, created_at=now + timedelta(microseconds=1),
            prompt_version=self.prompt.label if provider not in (None, "rules") else None,
            provider=provider, model=model,
        )  # fmt: skip
        reply.content_encrypted = self.cipher.encrypt(reply_text, str(reply.id))
        db.add_all([user_msg, reply])
        conv = db.get(CoachConversation, conversation_id)
        if conv is not None:
            conv.updated_at = now
        return user_msg, reply

    def _record(
        self,
        db: Session,
        user_id: uuid.UUID,
        provider: str,
        model: str,
        outcome: str,
        *,
        counts: bool,
        completion: Completion | None = None,
        output_estimate: int = 0,
        latency_ms: int = 0,
    ) -> None:
        db.add(
            AiUsageRecord(
                user_id=user_id,
                feature=FEATURE,
                provider=provider,
                model=model,
                prompt_version=self.prompt.label,
                outcome=outcome,
                counts_toward_limit=counts,
                input_tokens=completion.input_tokens if completion else 0,
                output_tokens=completion.output_tokens if completion else output_estimate,
                cache_read_tokens=completion.cache_read_tokens if completion else 0,
                latency_ms=latency_ms,
                created_at=_now(),
            )
        )

    def _stream(self, turn: PreparedTurn) -> Iterator[str]:
        started = time.monotonic()
        parts: list[str] = []
        completion: Completion | None = None
        blocked: str | None = None
        failure: ProviderError | None = None
        finished = False
        provider, model = self.provider.name, self.provider.model
        try:
            yield sse("start", {"conversation_id": str(turn.conversation_id)})
            chunks = self.provider.stream(turn.request)
            try:
                for chunk in chunks:
                    if isinstance(chunk, Completion):
                        completion = chunk
                        continue
                    blocked = blocked_output("".join(parts) + chunk, self.prompt.canary)
                    if blocked:
                        break  # stop generating: closing the stream cancels the provider request
                    parts.append(chunk)
                    yield sse("delta", {"text": chunk})
            except ProviderError as exc:
                failure = exc
            finally:
                close = getattr(chunks, "close", None)
                if close:
                    close()
            latency = int((time.monotonic() - started) * 1000)
            if completion is not None:
                model = completion.model
            text = "".join(parts).strip()

            with self._sessionmaker() as db:
                if failure is not None:
                    self._record(db, turn.user_id, provider, model, "error", counts=False, latency_ms=latency)
                    db.commit()
                    finished = True
                    yield sse(
                        "error",
                        {
                            "code": "coach_unavailable",
                            "message": "The coach couldn't reply just now. Your message wasn't saved, "
                            "so please try again.",
                            "retryable": failure.retryable,
                        },
                    )
                    return

                kind, flags, outcome = "message", [], "ok"
                if blocked:
                    kind, flags, outcome = "safety_replacement", [f"blocked:{blocked}"], f"blocked:{blocked}"
                    reply_text = SAFETY_REPLACEMENT
                elif completion is not None and completion.stop_reason == "refusal":
                    kind, flags, outcome = "safety_replacement", ["provider_refusal"], "refusal"
                    reply_text = REFUSAL_REPLACEMENT
                elif not text:
                    kind, flags, outcome = "safety_replacement", ["empty_reply"], "empty"
                    reply_text = REFUSAL_REPLACEMENT
                else:
                    reply_text = text
                    flags = grounding_flags(text, turn.request.facts)
                    if completion is not None and completion.stop_reason == "max_tokens":
                        flags.append("truncated")
                if kind != "message":
                    if parts:
                        yield sse("retract", {"reason": "safety"})
                    yield sse("delta", {"text": reply_text})

                user_msg, reply = self._persist(
                    db, turn.conversation_id, turn.text, turn.input_flags, reply_text, kind, flags,
                    provider=provider, model=model,
                )  # fmt: skip
                if blocked:
                    db.add(
                        AuditEvent(
                            event_type="coach.output_blocked",
                            subject_type="coach_conversation",
                            subject_id=str(turn.conversation_id),
                            details={"rule": blocked},
                        )
                    )
                self._record(
                    db, turn.user_id, provider, model, outcome, counts=True, completion=completion,
                    output_estimate=len(text) // 4, latency_ms=latency,
                )  # fmt: skip
                try:
                    db.commit()
                except SQLAlchemyError:
                    db.rollback()
                    finished = True
                    yield sse(
                        "error",
                        {"code": "coach_save_failed", "message": "Your conversation couldn't be saved. "
                         "Please try again.", "retryable": True},
                    )  # fmt: skip
                    return
                finished = True
                yield sse("done", self._done(db, turn.user_id, user_msg, reply))
        finally:
            if not finished:
                # The client went away mid-reply. The provider may still have charged for it.
                try:
                    with self._sessionmaker() as db:
                        self._record(
                            db, turn.user_id, provider, model, "client_disconnected", counts=True,
                            completion=completion, output_estimate=len("".join(parts)) // 4,
                        )  # fmt: skip
                        db.commit()
                except SQLAlchemyError:
                    pass
            self._release(turn.conversation_id)


def result_kind(r: AssessmentResult) -> str:
    if r.archetype_version is not None:
        return "big_five"
    return "interests" if r.interest_profile is not None else "leadership"
