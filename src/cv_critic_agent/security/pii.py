"""Fernet-based symmetric encryption for PII at rest.

Used to protect requester email and motive on the JSON store. The key is
held in `FERNET_KEY` env var on Render and never written to git.

Why Fernet rather than raw AES:
- Built-in authentication (HMAC-SHA256 inside) — tampering returns None.
- Versioned format with the timestamp baked in — would let us layer rate
  limiting on token age later.
- Library-provided, audited primitive — no nonce or IV mistakes possible.

This module never reads the environment. Callers pass the key explicitly so
rotation reduces to "swap one constant" and every test is self-contained.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


def encrypt_pii(plaintext: str, key: bytes) -> str:
    """Return the Fernet ciphertext as an ASCII string (URL-safe base64)."""
    if not isinstance(plaintext, str):
        raise TypeError("plaintext must be str")
    if not plaintext:
        raise ValueError("plaintext must be non-empty")
    return Fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_pii(ciphertext: str, key: bytes) -> str | None:
    """Return plaintext, or None on tampering, wrong key, or malformed input.

    Never raises. The caller treats None as "untrusted value", never as a bug.
    """
    if not isinstance(ciphertext, str) or not ciphertext:
        return None
    try:
        return Fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return None
