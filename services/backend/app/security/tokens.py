"""Opaque resume tokens for anonymous assessment sessions.

A token is shown to the client once. Only its SHA-256 is stored, so a database leak does not
expose usable tokens. Comparison is constant-time.
"""

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_matches(token: str | None, expected_hash: str) -> bool:
    if not token or len(token) > 256:
        return False
    return hmac.compare_digest(hash_token(token), expected_hash)
