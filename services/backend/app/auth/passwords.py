"""Password hashing (Argon2id) and policy (NIST SP 800-63B style: length, not composition rules)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id with library defaults (RFC 9106 low-memory profile)

MIN_LENGTH = 10
MAX_LENGTH = 128
# Small built-in deny list; extend with a breached-password check (k-anonymity API) when approved.
_COMMON = {
    "password",
    "password1",
    "password12",
    "password123",
    "password1234",
    "1234567890",
    "12345678910",
    "qwertyuiop",
    "iloveyou12",
    "letmein123",
    "welcome123",
    "admin12345",
    "abc1234567",
    "personality",
    "personalitydna",
    "qwerty1234",
    "1q2w3e4r5t",
    "0987654321",
    "1111111111",
    "aaaaaaaaaa",
}


def password_problem(password: str, email: str | None = None) -> str | None:
    """Return a user-facing reason the password is unacceptable, or None."""
    if len(password) < MIN_LENGTH:
        return f"Use at least {MIN_LENGTH} characters."
    if len(password) > MAX_LENGTH:
        return f"Use at most {MAX_LENGTH} characters."
    lowered = password.lower()
    if lowered in _COMMON or len(set(lowered)) < 4:
        return "This password is too easy to guess. Try a longer phrase."
    if email and lowered == email.lower().split("@")[0]:
        return "Don't use your email address as your password."
    return None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# Used to equalize timing when the account does not exist.
DUMMY_HASH = _hasher.hash("timing-equalizer-not-a-real-password")
