"""HMAC-signed expiring tokens.

A minimal JWT-like format: `<base64url(payload_json)>.<base64url(hmac)>`.
Used everywhere a value must travel through email or a query string and come
back trustworthy: owner decision links, requester session tokens, magic-link
admin auth, the GDPR deletion confirmation, ...

Design notes:
- Signature comparison uses `hmac.compare_digest` to defeat timing attacks.
- Expiry is encoded in the payload as `exp` (unix seconds); verify rejects
  expired tokens.
- This module is environment-free: the secret is always passed in. That
  makes rotation a matter of swapping a constant in the caller, and makes
  every test self-contained.
- `verify_token` never raises on malformed input — it returns None. Callers
  treat that as "untrusted token", not as a programming error.
"""
from __future__ import annotations

import base64
import hmac
import json
import time
from hashlib import sha256
from typing import Any


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = (-len(text)) % 4
    return base64.urlsafe_b64decode(text + "=" * pad)


def sign_token(payload: dict[str, Any], secret: bytes, ttl_seconds: int) -> str:
    """Build a self-contained, signed, expiring token safe to embed in URLs."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be > 0")
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl_seconds
    encoded = _b64url_encode(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = _b64url_encode(
        hmac.new(secret, encoded.encode("ascii"), sha256).digest()
    )
    return f"{encoded}.{signature}"


def verify_token(token: str, secret: bytes) -> dict[str, Any] | None:
    """Return decoded payload if signature and expiry are valid, else None."""
    if not isinstance(token, str) or "." not in token:
        return None
    try:
        encoded, signature = token.split(".", 1)
    except ValueError:
        return None
    if not encoded or not signature:
        return None

    expected = _b64url_encode(
        hmac.new(secret, encoded.encode("ascii"), sha256).digest()
    )
    if not hmac.compare_digest(expected, signature):
        return None

    try:
        payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    return payload
