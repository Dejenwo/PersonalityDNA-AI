"""Account lifecycle: registration, email verification, login, refresh rotation, password reset, deletion."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.auth.passwords import DUMMY_HASH, hash_password, needs_rehash, password_problem, verify_password
from app.auth.schemas import AttributionIn
from app.core.config import Settings
from app.database.models import AuditEvent, AuthToken, ConsentRecord, RefreshToken, User
from app.marketing.service import record_acquisition
from app.notifications.email import OutgoingEmail
from app.notifications.service import NotificationService
from app.organizations.service import before_account_deletion
from app.security.consent import CURRENT_POLICY_VERSION
from app.security.tokens import hash_token, new_token

ACCOUNT_CONSENT_TYPE = "account_terms_privacy"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _audit(db: Session, event: str, user_id: uuid.UUID | None, **details: object) -> None:
    db.add(AuditEvent(event_type=event, subject_type="user", subject_id=str(user_id or "-"), details=details))


@dataclass
class Mailer:
    settings: Settings

    def _link(self, path: str, token: str) -> str:
        # Token in the fragment so it never reaches server logs or referrers.
        return f"{self.settings.web_base_url.rstrip('/')}{path}#token={token}"

    def verify(self, to: str, token: str) -> OutgoingEmail:
        return OutgoingEmail(
            to=to,
            kind="verify_email",
            subject="Confirm your PersonalityDNA email",
            text=(
                "Welcome to PersonalityDNA.\n\nConfirm your email address by opening this link:\n"
                f"{self._link('/verify-email', token)}\n\n"
                f"The link expires in {self.settings.email_token_hours} hours. "
                "If you didn't create an account, you can ignore this email."
            ),
        )

    def already_registered(self, to: str) -> OutgoingEmail:
        return OutgoingEmail(
            to=to,
            kind="already_registered",
            subject="You already have a PersonalityDNA account",
            text=(
                "Someone (hopefully you) tried to create a PersonalityDNA account with this email, "
                "but one already exists.\n\nYou can sign in, or reset your password here:\n"
                f"{self.settings.web_base_url.rstrip('/')}/forgot-password\n\n"
                "If this wasn't you, no action is needed."
            ),
        )

    def reset(self, to: str, token: str) -> OutgoingEmail:
        return OutgoingEmail(
            to=to,
            kind="reset_password",
            subject="Reset your PersonalityDNA password",
            text=(
                "Use this link to choose a new password:\n"
                f"{self._link('/reset-password', token)}\n\n"
                f"The link expires in {self.settings.password_reset_minutes} minutes and works once. "
                "If you didn't ask for this, you can ignore this email."
            ),
        )


class AuthService:
    def __init__(self, settings: Settings, notifications: NotificationService | None = None) -> None:
        self.s = settings
        self.mail = Mailer(settings)
        self.notifications = notifications

    def _security_notice(self, db: Session, user: User | None, title: str, body: str, link: str) -> None:
        # Security notices can't be turned off (see notifications.KINDS).
        if user is not None and self.notifications is not None:
            self.notifications.notify(db, user, "security", title, body, link)

    # ---- tokens emailed to users -------------------------------------------------------
    def _email_token(self, db: Session, user: User, purpose: str, ttl: timedelta) -> str:
        # Only the newest token of a purpose stays valid.
        db.execute(
            update(AuthToken)
            .where(AuthToken.user_id == user.id, AuthToken.purpose == purpose, AuthToken.used_at.is_(None))
            .values(used_at=_now())
        )
        raw = new_token()
        db.add(
            AuthToken(user_id=user.id, purpose=purpose, token_hash=hash_token(raw), expires_at=_now() + ttl)
        )
        return raw

    def _consume(self, db: Session, raw: str, purpose: str) -> User:
        row = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(raw[:256])))
        if (
            row is None
            or row.purpose != purpose
            or row.used_at is not None
            or _aware(row.expires_at) <= _now()
        ):
            raise ApiError(
                400, "invalid_token", "This link is invalid or has expired. Please request a new one."
            )
        row.used_at = _now()
        user = db.get(User, row.user_id)
        if user is None or user.status != "active":
            raise ApiError(
                400, "invalid_token", "This link is invalid or has expired. Please request a new one."
            )
        return user

    # ---- registration and verification --------------------------------------------------
    def register(
        self,
        db: Session,
        *,
        email: str,
        password: str,
        display_name: str | None,
        accepted_terms: bool,
        age_confirmed: bool,
        policy_version: str,
        attribution: AttributionIn | None = None,
    ) -> list[OutgoingEmail]:
        if not accepted_terms:
            raise ApiError(422, "consent_required", "Please accept the terms and privacy notice.")
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
        email = normalize_email(email)
        problem = password_problem(password, email)
        if problem:
            raise ApiError(422, "weak_password", problem)

        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            # Same response as a new registration, so the endpoint can't be used to discover accounts.
            if existing.email_verified_at is None:
                return [self.mail.verify(email, self._commit_token(db, existing, "verify_email"))]
            db.commit()
            return [self.mail.already_registered(email)]

        user = User(email=email, password_hash=hash_password(password), display_name=display_name)
        db.add(user)
        db.flush()
        db.add(
            ConsentRecord(
                user_id=user.id,
                consent_type=ACCOUNT_CONSENT_TYPE,
                policy_version=policy_version,
                granted=True,
                age_confirmed_18_plus=True,
            )
        )
        if attribution is not None:
            record_acquisition(
                db,
                user.id,
                attribution.referral,
                attribution.source,
                attribution.medium,
                attribution.campaign,
            )
        _audit(db, "user.registered", user.id)
        return [self.mail.verify(email, self._commit_token(db, user, "verify_email"))]

    def _commit_token(self, db: Session, user: User, purpose: str) -> str:
        ttl = (
            timedelta(hours=self.s.email_token_hours)
            if purpose == "verify_email"
            else timedelta(minutes=self.s.password_reset_minutes)
        )
        raw = self._email_token(db, user, purpose, ttl)
        db.commit()
        return raw

    def verify_email(self, db: Session, raw: str) -> User:
        user = self._consume(db, raw, "verify_email")
        if user.email_verified_at is None:
            user.email_verified_at = _now()
            _audit(db, "user.email_verified", user.id)
        db.commit()
        return user

    def resend_verification(self, db: Session, email: str) -> list[OutgoingEmail]:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None or user.email_verified_at is not None or user.status != "active":
            return []
        return [self.mail.verify(user.email, self._commit_token(db, user, "verify_email"))]

    # ---- login and sessions --------------------------------------------------------------
    def authenticate(self, db: Session, email: str, password: str) -> User:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            verify_password(DUMMY_HASH, password)  # equalize timing
            raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
        if not verify_password(user.password_hash, password) or user.status != "active":
            _audit(db, "user.login_failed", user.id)
            db.commit()
            raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
        if user.email_verified_at is None:
            raise ApiError(
                403, "email_unverified", "Please confirm your email address first. We can send a new link."
            )
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        _audit(db, "user.login", user.id)
        db.commit()
        return user

    def issue_refresh(self, db: Session, user: User, family_id: uuid.UUID | None = None) -> str:
        raw = new_token()
        db.add(
            RefreshToken(
                user_id=user.id,
                family_id=family_id or uuid.uuid4(),
                token_hash=hash_token(raw),
                expires_at=_now() + timedelta(days=self.s.refresh_token_days),
            )
        )
        db.commit()
        return raw

    def rotate_refresh(self, db: Session, raw: str | None) -> tuple[User, str]:
        invalid = ApiError(401, "invalid_session", "Your session has ended. Please sign in again.")
        if not raw or len(raw) > 256:
            raise invalid
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if row is None or row.revoked_at is not None or _aware(row.expires_at) <= _now():
            raise invalid
        if row.rotated_at is not None:
            # A rotated token came back: assume theft and end every session in the family.
            db.execute(
                update(RefreshToken).where(RefreshToken.family_id == row.family_id).values(revoked_at=_now())
            )
            _audit(db, "user.refresh_reuse_detected", row.user_id)
            self._security_notice(
                db,
                db.get(User, row.user_id),
                "We signed you out everywhere",
                "An old sign-in session was used again, so we ended every session on your account as a "
                "precaution. Sign in again. If you didn't expect this, reset your password.",
                "/login",
            )
            db.commit()
            raise invalid
        user = db.get(User, row.user_id)
        if user is None or user.status != "active":
            raise invalid
        row.rotated_at = _now()
        return user, self.issue_refresh(db, user, row.family_id)

    def revoke_refresh(self, db: Session, raw: str | None) -> None:
        if not raw:
            return
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw[:256])))
        if row is not None:
            db.execute(
                update(RefreshToken).where(RefreshToken.family_id == row.family_id).values(revoked_at=_now())
            )
            db.commit()

    def revoke_all(self, db: Session, user_id: uuid.UUID) -> None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_now())
        )

    # ---- password reset -------------------------------------------------------------------
    def request_reset(self, db: Session, email: str) -> list[OutgoingEmail]:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None or user.status != "active":
            return []
        return [self.mail.reset(user.email, self._commit_token(db, user, "reset_password"))]

    def reset_password(self, db: Session, raw: str, new_password: str) -> None:
        user = self._consume(db, raw, "reset_password")
        problem = password_problem(new_password, user.email)
        if problem:
            db.rollback()
            raise ApiError(422, "weak_password", problem)
        user.password_hash = hash_password(new_password)
        user.password_changed_at = _now()
        # Following a reset link proves control of the inbox.
        user.email_verified_at = user.email_verified_at or _now()
        self.revoke_all(db, user.id)
        _audit(db, "user.password_reset", user.id)
        self._security_notice(
            db,
            user,
            "Your password was changed",
            "Your PersonalityDNA password was just changed and every session was signed out. "
            "If this wasn't you, reset your password straight away.",
            "/forgot-password",
        )
        db.commit()

    # ---- deletion -------------------------------------------------------------------------
    def delete_account(self, db: Session, user: User, password: str) -> None:
        if not verify_password(user.password_hash, password):
            raise ApiError(403, "invalid_credentials", "Password is incorrect.")
        user_id = user.id
        before_account_deletion(db, user_id)
        db.execute(delete(User).where(User.id == user_id))
        _audit(db, "user.deleted", user_id)
        db.commit()
