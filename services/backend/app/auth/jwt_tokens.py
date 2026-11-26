"""Short-lived access tokens (JWT, HS256)."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    issued_at: datetime


class TokenError(Exception):
    pass


class AccessTokenCodec:
    def __init__(self, settings: Settings) -> None:
        secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None
        # Development/test without a configured secret: random per process (tokens die on restart).
        self._key = secret or secrets.token_urlsafe(48)
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience
        self.ttl = timedelta(minutes=settings.access_token_minutes)

    def issue(self, user_id: uuid.UUID, now: datetime | None = None) -> tuple[str, datetime]:
        now = now or datetime.now(UTC)
        exp = now + self.ttl
        payload = {
            "sub": str(user_id),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "typ": "access",
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, self._key, algorithm="HS256"), exp

    def decode(self, token: str) -> AccessClaims:
        try:
            data = jwt.decode(
                token,
                self._key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["sub", "exp", "iat", "iss", "aud"]},
            )
            if data.get("typ") != "access":
                raise TokenError("wrong token type")
            return AccessClaims(uuid.UUID(data["sub"]), datetime.fromtimestamp(data["iat"], UTC))
        except (jwt.PyJWTError, ValueError) as exc:
            raise TokenError(str(exc)) from exc
