"""Negative-first tests for HMAC token signing.

Each test names a specific attack we block. A token round-trip is included
only to anchor the negative tests against a known-good baseline.
"""
from __future__ import annotations

import base64
import json
import time
import unittest
from unittest import mock

from cv_critic_agent.security.crypto import sign_token, verify_token

SECRET = b"\x00" * 32
OTHER_SECRET = b"\xff" * 32


class CryptoTests(unittest.TestCase):
    def test_round_trip_preserves_payload(self) -> None:
        token = sign_token({"user": "alice", "role": "owner"}, SECRET, ttl_seconds=60)
        payload = verify_token(token, SECRET)
        assert payload is not None
        self.assertEqual(payload["user"], "alice")
        self.assertEqual(payload["role"], "owner")
        self.assertIn("exp", payload)

    def test_forged_signature_rejected(self) -> None:
        token = sign_token({"user": "alice"}, SECRET, ttl_seconds=60)
        body, _ = token.split(".", 1)
        forged = f"{body}.AAAAAAAAAAAAAAAAAAAAAAAA"
        self.assertIsNone(verify_token(forged, SECRET))

    def test_wrong_secret_rejected(self) -> None:
        token = sign_token({"user": "alice"}, SECRET, ttl_seconds=60)
        self.assertIsNone(verify_token(token, OTHER_SECRET))

    def test_payload_tampering_rejected(self) -> None:
        token = sign_token({"user": "alice"}, SECRET, ttl_seconds=60)
        _, signature = token.split(".", 1)
        bad_body = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"user": "admin", "exp": int(time.time()) + 60},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            .rstrip(b"=")
            .decode()
        )
        forged = f"{bad_body}.{signature}"
        self.assertIsNone(verify_token(forged, SECRET))

    def test_expired_token_rejected(self) -> None:
        token = sign_token({"user": "alice"}, SECRET, ttl_seconds=60)
        with mock.patch(
            "cv_critic_agent.security.crypto.time.time",
            return_value=time.time() + 3600,
        ):
            self.assertIsNone(verify_token(token, SECRET))

    def test_malformed_input_returns_none(self) -> None:
        bad_cases = ["", "no_dot_at_all", "....", ".a", "a.", "a.b.c.d"]
        for bad in bad_cases:
            with self.subTest(token=bad):
                self.assertIsNone(verify_token(bad, SECRET))

    def test_non_string_input_returns_none(self) -> None:
        self.assertIsNone(verify_token(None, SECRET))  # type: ignore[arg-type]
        self.assertIsNone(verify_token(123, SECRET))  # type: ignore[arg-type]
        self.assertIsNone(verify_token(b"bytes", SECRET))  # type: ignore[arg-type]

    def test_compare_digest_is_used_not_equal(self) -> None:
        token = sign_token({"x": 1}, SECRET, ttl_seconds=60)
        with mock.patch(
            "cv_critic_agent.security.crypto.hmac.compare_digest",
            return_value=False,
        ) as cd:
            self.assertIsNone(verify_token(token, SECRET))
            cd.assert_called_once()

    def test_ttl_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            sign_token({"x": 1}, SECRET, ttl_seconds=0)
        with self.assertRaises(ValueError):
            sign_token({"x": 1}, SECRET, ttl_seconds=-1)

    def test_signed_token_is_url_safe(self) -> None:
        token = sign_token({"user": "alice"}, SECRET, ttl_seconds=60)
        for forbidden in ("/", "+", "=", " ", "\n"):
            self.assertNotIn(forbidden, token)


if __name__ == "__main__":
    unittest.main()
