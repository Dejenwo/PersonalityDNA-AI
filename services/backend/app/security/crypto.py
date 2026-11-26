"""Field-level encryption for sensitive free text (coaching messages).

AES-256-GCM with a random 96-bit nonce per value. The record id is bound as associated data, so a
ciphertext copied onto another row fails to decrypt. Stored format: ``v1:<base64url(nonce||ciphertext)>``.
The version prefix leaves room for key rotation.
"""

import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings

_PREFIX = "v1:"
# Development and test only. The production guard in Settings refuses to start without a real key.
_DEV_KEY = hashlib.sha256(b"personalitydna-development-only-key").digest()


class DecryptionError(Exception):
    pass


class FieldCipher:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("The data encryption key must be 32 bytes")
        self._aead = AESGCM(key)

    @classmethod
    def from_settings(cls, settings: Settings) -> "FieldCipher":
        if settings.data_encryption_key is None:
            return cls(_DEV_KEY)
        raw = settings.data_encryption_key.get_secret_value().strip()
        try:
            key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        except ValueError as exc:
            raise ValueError("PDNA_DATA_ENCRYPTION_KEY must be base64 encoded") from exc
        return cls(key)

    def encrypt(self, plaintext: str, context: str) -> str:
        nonce = os.urandom(12)
        sealed = self._aead.encrypt(nonce, plaintext.encode("utf-8"), context.encode("utf-8"))
        return _PREFIX + base64.urlsafe_b64encode(nonce + sealed).decode("ascii")

    def decrypt(self, stored: str, context: str) -> str:
        if not stored.startswith(_PREFIX):
            raise DecryptionError("Unknown ciphertext format")
        try:
            blob = base64.urlsafe_b64decode(stored[len(_PREFIX) :])
            return self._aead.decrypt(blob[:12], blob[12:], context.encode("utf-8")).decode("utf-8")
        except (InvalidTag, ValueError) as exc:
            raise DecryptionError("Ciphertext could not be decrypted") from exc
