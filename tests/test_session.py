"""Tests for security.session.verify_session.

Negative-first: forgery, expiry, malformation, wrong sub, missing req.
Then state-machine checks (not approved, IP bind, quota). Happy path last.
"""
from __future__ import annotations

import base64
import hmac
import json
import tempfile
import time
import unittest
from hashlib import sha256
from pathlib import Path

from cryptography.fernet import Fernet

from cv_critic_agent.access_requests.models import (
    AccessRequest,
    AccessRequestStatus,
)
from cv_critic_agent.access_requests.store import AccessRequestStore
from cv_critic_agent.security.crypto import sign_token
from cv_critic_agent.security.session import (
    InvalidSessionToken,
    SessionIpMismatch,
    SessionNotApproved,
    SessionQuotaExceeded,
    verify_session,
)

SECRET = b"sprint-5-secret"
FERNET_KEY = Fernet.generate_key()
SESSION_TTL = 24 * 3600


# ── Helpers ───────────────────────────────────────────────────────────────────


def _approved_in_store(store: AccessRequestStore) -> AccessRequest:
    req = AccessRequest.new(
        name="Alice",
        company="ACME",
        email="alice@example.com",
        motive="test",
        requester_ip="1.1.1.1",
    )
    req.approve()
    store.create(req)
    return req


def _store_in(base_dir: Path) -> AccessRequestStore:
    return AccessRequestStore(base_dir=base_dir, fernet_key=FERNET_KEY)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_token(payload: dict, secret: bytes = SECRET) -> str:
    """Manually craft a signed token without any TTL validation, so callers
    can force expired/sub-mismatch/etc. payloads ``sign_token`` would reject."""
    encoded = _b64url(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(secret, encoded.encode("ascii"), sha256).digest())
    return f"{encoded}.{sig}"


class TempStoreMixin(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="cv-critic-session-")
        self.base_dir = Path(self._tmp.name)
        self.store = _store_in(self.base_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()


# ── Token-level failures (InvalidSessionToken) ────────────────────────────────


class InvalidTokenTests(TempStoreMixin):
    def test_empty_request_ip_raises_invalid(self) -> None:
        ar = _approved_in_store(self.store)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "", SECRET, self.store)

    def test_garbage_token_raises_invalid(self) -> None:
        with self.assertRaises(InvalidSessionToken):
            verify_session("not.a.token", "1.1.1.1", SECRET, self.store)

    def test_forged_signature_raises_invalid(self) -> None:
        ar = _approved_in_store(self.store)
        good = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        encoded, _sig = good.split(".", 1)
        tampered = f"{encoded}.{_b64url(b'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')}"
        with self.assertRaises(InvalidSessionToken):
            verify_session(tampered, "1.1.1.1", SECRET, self.store)

    def test_wrong_secret_raises_invalid(self) -> None:
        ar = _approved_in_store(self.store)
        token = sign_token({"sub": "session", "req": ar.id}, b"other-secret", SESSION_TTL)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_expired_token_raises_invalid(self) -> None:
        ar = _approved_in_store(self.store)
        expired_payload = {
            "sub": "session",
            "req": ar.id,
            "exp": int(time.time()) - 60,
        }
        token = _make_token(expired_payload, SECRET)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_wrong_sub_raises_invalid(self) -> None:
        ar = _approved_in_store(self.store)
        token = sign_token({"sub": "decide", "req": ar.id}, SECRET, SESSION_TTL)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_missing_req_raises_invalid(self) -> None:
        token = sign_token({"sub": "session"}, SECRET, SESSION_TTL)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_empty_req_raises_invalid(self) -> None:
        token = sign_token({"sub": "session", "req": ""}, SECRET, SESSION_TTL)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_non_string_req_raises_invalid(self) -> None:
        token = sign_token({"sub": "session", "req": 12345}, SECRET, SESSION_TTL)
        with self.assertRaises(InvalidSessionToken):
            verify_session(token, "1.1.1.1", SECRET, self.store)


# ── State-machine failures ────────────────────────────────────────────────────


class SessionNotApprovedTests(TempStoreMixin):
    def test_unknown_req_id_raises_not_approved(self) -> None:
        token = sign_token({"sub": "session", "req": "nonexistent"}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionNotApproved):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_pending_request_raises_not_approved(self) -> None:
        req = AccessRequest.new(
            name="A", company="A", email="a@a.com", motive="m", requester_ip="1.1.1.1"
        )
        self.store.create(req)  # status = PENDING
        token = sign_token({"sub": "session", "req": req.id}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionNotApproved):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_rejected_request_raises_not_approved(self) -> None:
        req = AccessRequest.new(
            name="A", company="A", email="a@a.com", motive="m", requester_ip="1.1.1.1"
        )
        req.reject()
        self.store.create(req)
        token = sign_token({"sub": "session", "req": req.id}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionNotApproved):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_revoked_request_raises_not_approved(self) -> None:
        ar = _approved_in_store(self.store)
        ar.revoke()
        self.store.update(ar)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionNotApproved):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_consumed_request_raises_not_approved(self) -> None:
        ar = _approved_in_store(self.store)
        ar.runs_used = ar.runs_quota
        ar.status = AccessRequestStatus.CONSUMED
        self.store.update(ar)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionNotApproved):
            verify_session(token, "1.1.1.1", SECRET, self.store)


# ── IP binding ────────────────────────────────────────────────────────────────


class IpBindingTests(TempStoreMixin):
    def test_first_call_passes_with_no_ip_binding(self) -> None:
        ar = _approved_in_store(self.store)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        result = verify_session(token, "9.9.9.9", SECRET, self.store)
        self.assertEqual(result.id, ar.id)
        self.assertIsNone(result.session_ip_binding)  # not mutated by verify

    def test_matching_ip_passes(self) -> None:
        ar = _approved_in_store(self.store)
        ar.session_ip_binding = "9.9.9.9"
        self.store.update(ar)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        result = verify_session(token, "9.9.9.9", SECRET, self.store)
        self.assertEqual(result.session_ip_binding, "9.9.9.9")

    def test_mismatching_ip_raises(self) -> None:
        ar = _approved_in_store(self.store)
        ar.session_ip_binding = "1.1.1.1"
        self.store.update(ar)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionIpMismatch):
            verify_session(token, "2.2.2.2", SECRET, self.store)


# ── Quota ─────────────────────────────────────────────────────────────────────


class QuotaTests(TempStoreMixin):
    def test_quota_exhausted_raises(self) -> None:
        """Edge: status still APPROVED but counter already at quota (e.g. cron raced)."""
        ar = _approved_in_store(self.store)
        ar.runs_used = ar.runs_quota
        self.store.update(ar)  # status stays APPROVED here
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        with self.assertRaises(SessionQuotaExceeded):
            verify_session(token, "1.1.1.1", SECRET, self.store)

    def test_partial_quota_passes(self) -> None:
        ar = _approved_in_store(self.store)
        ar.runs_used = 1
        self.store.update(ar)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        result = verify_session(token, "1.1.1.1", SECRET, self.store)
        self.assertEqual(result.runs_used, 1)


# ── Verify does not mutate ────────────────────────────────────────────────────


class NoMutationTests(TempStoreMixin):
    def test_verify_does_not_change_store_state(self) -> None:
        ar = _approved_in_store(self.store)
        token = sign_token({"sub": "session", "req": ar.id}, SECRET, SESSION_TTL)
        before = self.store.get(ar.id)

        verify_session(token, "1.1.1.1", SECRET, self.store)

        after = self.store.get(ar.id)
        self.assertEqual(before.runs_used, after.runs_used)
        self.assertEqual(before.session_ip_binding, after.session_ip_binding)
        self.assertEqual(before.status, after.status)


if __name__ == "__main__":
    unittest.main()
