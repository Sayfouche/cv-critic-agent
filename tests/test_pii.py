"""Negative-first tests for Fernet PII encryption."""
from __future__ import annotations

import unittest

from cryptography.fernet import Fernet

from cv_critic_agent.security.pii import decrypt_pii, encrypt_pii

KEY = Fernet.generate_key()
OTHER_KEY = Fernet.generate_key()


class PiiTests(unittest.TestCase):
    def test_round_trip_preserves_value(self) -> None:
        ciphertext = encrypt_pii("alice@example.com", KEY)
        self.assertEqual(decrypt_pii(ciphertext, KEY), "alice@example.com")

    def test_ciphertext_is_not_plaintext(self) -> None:
        ciphertext = encrypt_pii("alice@example.com", KEY)
        self.assertNotIn("alice", ciphertext)
        self.assertNotIn("example.com", ciphertext)

    def test_wrong_key_returns_none(self) -> None:
        ciphertext = encrypt_pii("alice@example.com", KEY)
        self.assertIsNone(decrypt_pii(ciphertext, OTHER_KEY))

    def test_tampered_ciphertext_returns_none(self) -> None:
        ciphertext = encrypt_pii("alice@example.com", KEY)
        tampered = ciphertext[:-2] + "AA"
        self.assertIsNone(decrypt_pii(tampered, KEY))

    def test_malformed_input_returns_none(self) -> None:
        for bad in ["", "not-a-fernet-token", "x", "....", "Z" * 50]:
            with self.subTest(ciphertext=bad):
                self.assertIsNone(decrypt_pii(bad, KEY))

    def test_non_string_input_returns_none(self) -> None:
        self.assertIsNone(decrypt_pii(None, KEY))  # type: ignore[arg-type]
        self.assertIsNone(decrypt_pii(123, KEY))  # type: ignore[arg-type]
        self.assertIsNone(decrypt_pii(b"bytes", KEY))  # type: ignore[arg-type]

    def test_empty_plaintext_rejected(self) -> None:
        with self.assertRaises(ValueError):
            encrypt_pii("", KEY)

    def test_non_string_plaintext_rejected(self) -> None:
        with self.assertRaises(TypeError):
            encrypt_pii(123, KEY)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            encrypt_pii(None, KEY)  # type: ignore[arg-type]

    def test_unicode_preserved(self) -> None:
        for sample in ["café", "ölü", "日本語", "🤖"]:
            with self.subTest(sample=sample):
                self.assertEqual(decrypt_pii(encrypt_pii(sample, KEY), KEY), sample)


if __name__ == "__main__":
    unittest.main()
