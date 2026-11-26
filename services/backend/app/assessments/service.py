"""Assessment session workflow: create, save answers, resume, complete."""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import ApiError
from app.assessments.content import ContentBundle, Instrument, LoadedFile
from app.careers.interests import interest_profile
from app.database.models import (
    AssessmentResponse,
    AssessmentResult,
    AssessmentSession,
    AssessmentVersion,
    AuditEvent,
    ConsentRecord,
    TraitScore,
)
from app.personality.archetypes import match_archetypes
from app.scoring.engine import ScoringError, score
from app.security.consent import ASSESSMENT_CONSENT_TYPE, CURRENT_POLICY_VERSION
from app.security.tokens import hash_token, new_token, token_matches

NOT_FOUND = ApiError(404, "not_found", "Assessment session not found.")


def latest_version(bundle: ContentBundle, instrument_id: str) -> LoadedFile[Instrument]:
    candidates = [f for k, f in bundle.instruments.items() if k.split("@")[0] == instrument_id]
    if not candidates:
        raise ApiError(404, "not_found", "Assessment not found.")
    return max(candidates, key=lambda f: tuple(int(p) for p in f.data.version.split(".")))


def _audit(db: Session, event_type: str, subject_type: str, subject_id: object, **details: object) -> None:
    db.add(
        AuditEvent(
            event_type=event_type, subject_type=subject_type, subject_id=str(subject_id), details=details
        )
    )


def create_session(
    db: Session,
    bundle: ContentBundle,
    *,
    instrument_id: str,
    version: str | None,
    locale: str,
    accepted: bool,
    age_confirmed: bool,
    policy_version: str,
    user_id: uuid.UUID | None = None,
) -> tuple[AssessmentSession, str]:
    if not accepted:
        raise ApiError(422, "consent_required", "Consent is required to take an assessment.")
    if not age_confirmed:
        raise ApiError(
            422, "age_requirement", "PersonalityDNA is currently available to adults aged 18 and over."
        )
    if policy_version != CURRENT_POLICY_VERSION:
        raise ApiError(
            409,
            "consent_outdated",
            "The privacy notice has changed. Please review it again.",
            {"current_policy_version": CURRENT_POLICY_VERSION},
        )
    loaded = (
        latest_version(bundle, instrument_id)
        if version is None
        else _get_instrument(bundle, instrument_id, version)
    )
    if locale != loaded.data.locale:
        raise ApiError(
            422, "locale_unavailable", f"This assessment is only available in '{loaded.data.locale}'."
        )

    version_row = db.scalar(
        select(AssessmentVersion).where(
            AssessmentVersion.instrument_id == loaded.data.id,
            AssessmentVersion.version == loaded.data.version,
        )
    )
    if version_row is None or not version_row.is_active:
        raise ApiError(404, "not_found", "Assessment not found.")

    consent = ConsentRecord(
        consent_type=ASSESSMENT_CONSENT_TYPE,
        policy_version=policy_version,
        granted=True,
        age_confirmed_18_plus=True,
    )
    db.add(consent)
    db.flush()
    token = new_token()
    session = AssessmentSession(
        version_id=version_row.id,
        consent_id=consent.id,
        token_hash=hash_token(token),
        locale=locale,
        user_id=user_id,
    )
    db.add(session)
    db.flush()
    _audit(
        db,
        "assessment_session.created",
        "assessment_session",
        session.id,
        instrument=loaded.data.id,
        version=loaded.data.version,
    )
    db.commit()
    db.refresh(session)
    return session, token


def _get_instrument(bundle: ContentBundle, instrument_id: str, version: str) -> LoadedFile[Instrument]:
    key = f"{instrument_id}@{version}"
    if key not in bundle.instruments:
        raise ApiError(404, "not_found", "Assessment not found.")
    return bundle.instruments[key]


def _owner_or_token(
    owner_id: uuid.UUID | None, token_hash: str, token: str | None, user_id: uuid.UUID | None
) -> bool:
    if user_id is not None and owner_id == user_id:
        return True
    return token_matches(token, token_hash)


def get_authorized_session(
    db: Session, session_id: uuid.UUID, token: str | None, user_id: uuid.UUID | None = None
) -> AssessmentSession:
    session = db.scalar(
        select(AssessmentSession)
        .where(AssessmentSession.id == session_id)
        .options(selectinload(AssessmentSession.responses), selectinload(AssessmentSession.version))
    )
    # Same response for "missing" and "wrong token" so ids cannot be probed.
    if session is None or not _owner_or_token(session.user_id, session.token_hash, token, user_id):
        raise NOT_FOUND
    return session


def instrument_for(bundle: ContentBundle, session: AssessmentSession) -> LoadedFile[Instrument]:
    return _get_instrument(bundle, session.version.instrument_id, session.version.version)


def answers_of(session: AssessmentSession) -> dict[str, int]:
    return {r.item_id: r.value for r in session.responses}


def save_answers(
    db: Session, bundle: ContentBundle, session: AssessmentSession, answers: Iterable[tuple[str, int | None]]
) -> int:
    if session.status != "in_progress":
        raise ApiError(409, "session_closed", "This assessment has already been completed.")
    instrument = instrument_for(bundle, session).data
    rs = instrument.response_scale
    incoming: dict[str, int | None] = {}
    for item_id, value in answers:
        if item_id not in instrument.items_by_id:
            raise ApiError(422, "unknown_item", f"Unknown item {item_id!r}.")
        if value is not None and not rs.min <= value <= rs.max:
            raise ApiError(422, "invalid_answer", f"Answer must be between {rs.min} and {rs.max}.")
        incoming[item_id] = value  # last write wins within a request

    existing = {r.item_id: r for r in session.responses}
    now = datetime.now(UTC)
    for item_id, value in incoming.items():
        row = existing.get(item_id)
        if value is None:
            if row is not None:
                session.responses.remove(row)
        elif row is None:
            session.responses.append(AssessmentResponse(item_id=item_id, value=value, answered_at=now))
        else:
            row.value = value
            row.answered_at = now
    session.updated_at = now
    db.commit()
    db.refresh(session)
    return len(incoming)


def _elapsed_seconds(session: AssessmentSession, now: datetime) -> float:
    started = session.started_at
    if started.tzinfo is None:  # SQLite returns naive datetimes
        started = started.replace(tzinfo=UTC)
    return max((now - started).total_seconds(), 0.0)


def complete_session(db: Session, bundle: ContentBundle, session: AssessmentSession) -> AssessmentResult:
    if session.status == "completed" and session.result is not None:
        return session.result  # idempotent
    if session.status != "in_progress":
        raise ApiError(409, "session_closed", "This assessment can no longer be completed.")

    loaded = instrument_for(bundle, session)
    instrument = loaded.data
    answers = answers_of(session)
    now = datetime.now(UTC)
    try:
        output = score(instrument, answers, elapsed_seconds=_elapsed_seconds(session, now))
    except ScoringError as exc:  # pragma: no cover - answers are validated on save
        raise ApiError(422, "invalid_answers", str(exc)) from exc

    if not output.complete:
        missing = [i.id for i in instrument.items if i.id not in answers]
        insufficient = [s.scale_id for s in output.scales if s.status != "scored"]
        raise ApiError(
            422,
            "incomplete",
            "Please answer more questions before finishing.",
            {"missing_items": missing, "insufficient_scales": insufficient},
        )

    result = AssessmentResult(
        session_id=session.id,
        engine_version=output.engine_version,
        instrument_id=output.instrument_id,
        instrument_version=output.instrument_version,
        content_sha256=loaded.sha256,
        answers_sha256=output.answers_sha256,
        quality_flags=list(output.quality_flags),
    )
    if instrument.family == "big_five":
        scores = {s.scale_id: s.score for s in output.scales if s.score is not None}
        match = match_archetypes(bundle.archetypes.data, scores)
        result.archetype_version = match.version
        result.archetypes = {
            "weak_fit": match.weak_fit,
            "ranking": [
                {"id": f.id, "fit": f.fit, "drivers": [list(d) for d in f.drivers]} for f in match.ranking
            ],
        }
    else:
        profile = interest_profile({s.scale_id: int(s.raw_mean or 0) for s in output.scales})
        result.interest_profile = {
            "code": profile.code,
            "ranking": [[a, c] for a, c in profile.ranking],
            "boundary_ties": list(profile.boundary_ties),
            "empty": profile.empty,
        }
    for pos, s in enumerate(output.scales):
        result.trait_scores.append(
            TraitScore(
                trait=s.scale_id,
                position=pos,
                status=s.status,
                raw_mean=s.raw_mean,
                score=s.score,
                band=s.band,
                answered=s.answered,
                total=s.total,
            )
        )
    db.add(result)
    session.status = "completed"
    session.completed_at = now
    db.flush()
    _audit(
        db,
        "assessment_session.completed",
        "assessment_session",
        session.id,
        result_id=str(result.id),
        engine_version=output.engine_version,
        flags=list(output.quality_flags),
    )
    db.commit()
    db.refresh(result)
    return result


def get_authorized_result(
    db: Session, result_id: uuid.UUID, token: str | None, user_id: uuid.UUID | None = None
) -> AssessmentResult:
    result = db.scalar(
        select(AssessmentResult)
        .where(AssessmentResult.id == result_id)
        .options(selectinload(AssessmentResult.trait_scores), selectinload(AssessmentResult.session))
    )
    if result is None or not _owner_or_token(
        result.session.user_id, result.session.token_hash, token, user_id
    ):
        raise ApiError(404, "not_found", "Result not found.")
    return result


def claim_session(db: Session, session_id: uuid.UUID, token: str, user_id: uuid.UUID) -> AssessmentSession:
    """Attach an anonymous session to an account. Requires the session's resume token."""
    session = db.get(AssessmentSession, session_id)
    if session is None or not token_matches(token, session.token_hash):
        raise NOT_FOUND
    if session.user_id is not None and session.user_id != user_id:
        raise NOT_FOUND  # already owned by someone else; don't reveal that
    if session.user_id is None:
        session.user_id = user_id
        consent = db.get(ConsentRecord, session.consent_id)
        if consent is not None and consent.user_id is None:
            consent.user_id = user_id
        _audit(db, "assessment_session.claimed", "assessment_session", session.id)
        db.commit()
    return session
