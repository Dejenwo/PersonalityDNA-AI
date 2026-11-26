from datetime import UTC
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.errors import ApiError
from app.auth.jwt_tokens import AccessTokenCodec, TokenError
from app.database.models import User


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token else None


def _resolve(request: Request, db: Session, authorization: str | None) -> User | None:
    token = _bearer(authorization)
    if token is None:
        return None
    codec: AccessTokenCodec = request.app.state.access_tokens
    unauthorized = ApiError(401, "unauthorized", "Please sign in again.")
    try:
        claims = codec.decode(token)
    except TokenError as exc:
        raise unauthorized from exc
    user = db.get(User, claims.user_id)
    if user is None or user.status != "active":
        raise unauthorized
    changed = user.password_changed_at
    if changed is not None:
        changed = changed if changed.tzinfo else changed.replace(tzinfo=UTC)
        # Whole seconds on both sides, matching the JWT `iat` resolution.
        if int(claims.issued_at.timestamp()) < int(changed.timestamp()):
            raise unauthorized  # tokens issued before a password change are void
    return user


def optional_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    return _resolve(request, db, authorization)


def current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    user = _resolve(request, db, authorization)
    if user is None:
        raise ApiError(401, "unauthorized", "Please sign in.")
    return user


OptionalUser = Annotated[User | None, Depends(optional_user)]
CurrentUser = Annotated[User, Depends(current_user)]
