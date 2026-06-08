"""Sprint 4 endpoint tests — decision flow, admin, Telegram webhook.

Module-level setup creates a single TestClient with a real in-memory store
(tempdir) and mock HTTP factories for captcha + notifiers. All test classes
share the same client and store.

Test philosophy:
- Negative-first within each class (reject before happy path).
- One concern per test method.
- Direct store manipulation to pre-seed data without going through the full
  POST /api/access-requests flow (boundary isolation).

Running:
    python -m pytest tests/test_access_requests_endpoints.py -v
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from cryptography.fernet import Fernet

# ── module-level test fixtures ───────────────────────────────────────────────

_HMAC_KEY = "test-hmac-secret-key-sprint-4-ok"
_FERNET_KEY = Fernet.generate_key().decode()
_OWNER_CHAT_ID = "99999"
_OWNER_EMAIL = "owner@example.com"
_BASE_URL = "https://api.example.com"
_UI_URL = "https://ui.example.com"

_client = None
_client_ctx = None   # kept open so teardown can call __exit__
_store = None
_tmpdir: str | None = None
_env_patcher = None


class _MockResponse:
    def __init__(self, status_code: int, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict:
        return self._json


class _OkClient:
    """Mock HTTP client: always returns 200 ok."""

    async def __aenter__(self) -> _OkClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **_kwargs: Any) -> _MockResponse:
        return _MockResponse(200, {"ok": True, "success": True})


def _ok_factory(**_kwargs: object) -> _OkClient:
    return _OkClient()


def setUpModule() -> None:
    global _client, _client_ctx, _store, _tmpdir, _env_patcher

    _tmpdir = tempfile.mkdtemp()
    _env_patcher = mock.patch.dict(
        os.environ,
        {
            "HMAC_KEY": _HMAC_KEY,
            "FERNET_KEY": _FERNET_KEY,
            "TURNSTILE_SECRET": "test-turnstile-secret",
            "TELEGRAM_BOT_TOKEN": "test-bot-token",
            "TELEGRAM_OWNER_CHAT_ID": _OWNER_CHAT_ID,
            "RESEND_API_KEY": "re_test_key",
            "RESEND_FROM_ADDRESS": "noreply@example.com",
            "OWNER_EMAIL": _OWNER_EMAIL,
            "CV_CRITIC_BASE_URL": _BASE_URL,
            "CV_CRITIC_UI_URL": _UI_URL,
            "ACCESS_REQUESTS_DIR": _tmpdir,
        },
    )
    _env_patcher.start()

    # Import AFTER patching env so the lifespan picks up the test values.
    from fastapi.testclient import TestClient

    from cv_critic_agent.api import app

    # Use __enter__ so the lifespan (which reads env vars) actually runs.
    _client_ctx = TestClient(app)
    _client = _client_ctx.__enter__()

    # Override HTTP factories — they're live objects, not env var strings.
    app.state.captcha_http_factory = _ok_factory
    app.state.notifier_http_factory = _ok_factory

    _store = app.state.ar_store


def tearDownModule() -> None:
    global _env_patcher, _tmpdir, _client_ctx
    # Reset app.state so subsequent test modules without lifespan get clean
    # None values instead of inheriting our now-deleted tempdir-backed store.
    try:
        from cv_critic_agent.api import app

        app.state.ar_store = None
        app.state.budget_tracker = None
    except Exception:
        pass
    if _client_ctx is not None:
        try:
            _client_ctx.__exit__(None, None, None)
        except Exception:
            pass
    if _env_patcher:
        _env_patcher.stop()
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)


# ── helpers used by tests ─────────────────────────────────────────────────────

def _sign(payload: dict, ttl: int = 3600) -> str:
    from cv_critic_agent.security.crypto import sign_token

    return sign_token(payload, _HMAC_KEY.encode(), ttl)


def _sign_expired(payload: dict) -> str:
    """Build a validly-signed token whose exp is 1 second in the past.

    sign_token rejects ttl <= 0, so we build the token manually for
    negative-path tests that need to verify expired-token rejection.
    """
    import base64
    import hmac as hmac_mod
    import json
    import time
    from hashlib import sha256

    body = dict(payload)
    body["exp"] = int(time.time()) - 1  # already expired

    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    sig = base64.urlsafe_b64encode(
        hmac_mod.new(_HMAC_KEY.encode(), encoded.encode("ascii"), sha256).digest()
    ).rstrip(b"=").decode("ascii")
    return f"{encoded}.{sig}"


def _make_pending(
    *,
    name: str = "Alice",
    company: str = "ACME",
    email: str = "alice@example.com",
    motive: str = "test motive",
    ip: str = "1.2.3.4",
) -> "AccessRequest":
    from cv_critic_agent.access_requests.models import AccessRequest

    ar = AccessRequest.new(
        name=name, company=company, email=email, motive=motive, requester_ip=ip
    )
    _store.create(ar)
    return ar


def _valid_body(**overrides: Any) -> dict:
    base = {
        "name": "Bob",
        "company": "Initech",
        "email": "bob@example.com",
        "motive": "want to see the agent",
        "website": "",
    }
    base.update(overrides)
    return base


# ── POST /api/access-requests ─────────────────────────────────────────────────


class CreateAccessRequestTests(unittest.TestCase):
    """S4-1: POST /api/access-requests."""

    def _post(self, body: dict, ip: str = "10.0.0.1") -> Any:
        return _client.post(
            "/api/access-requests",
            json=body,
            headers={
                "cf-turnstile-response": "test-token",
                "X-Forwarded-For": ip,
            },
        )

    def test_honeypot_filled_returns_200_silently(self) -> None:
        body = _valid_body(website="http://spam.example.com")
        resp = self._post(body, ip="10.0.1.1")
        self.assertEqual(resp.status_code, 200)
        # Silently dropped — response says "pending" but no real store entry.
        data = resp.json()
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["id"], "bot")

    def test_missing_captcha_token_returns_403(self) -> None:
        resp = _client.post(
            "/api/access-requests",
            json=_valid_body(),
            headers={"X-Forwarded-For": "10.0.2.1"},
            # No cf-turnstile-response header → 403
        )
        self.assertEqual(resp.status_code, 403)

    def test_happy_path_returns_200_with_id_and_pending_status(self) -> None:
        resp = self._post(_valid_body(), ip="10.0.3.1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        self.assertNotEqual(data["id"], "bot")

    def test_happy_path_persists_to_store(self) -> None:
        resp = self._post(_valid_body(name="Stored Carol"), ip="10.0.4.1")
        self.assertEqual(resp.status_code, 200)
        req_id = resp.json()["id"]
        ar = _store.get(req_id)
        self.assertIsNotNone(ar)
        self.assertEqual(ar.name, "Stored Carol")

    def test_rate_limit_blocks_after_three_per_ip(self) -> None:
        ip = "10.99.99.1"
        for i in range(3):
            resp = self._post(_valid_body(name=f"User {i}"), ip=ip)
            self.assertEqual(resp.status_code, 200, f"request {i} should succeed")
        # 4th request from same IP — rate limited
        resp = self._post(_valid_body(name="User X"), ip=ip)
        self.assertEqual(resp.status_code, 429)


# ── GET /api/access-requests/{id}/status ─────────────────────────────────────


class GetStatusTests(unittest.TestCase):
    """S4-2: GET /api/access-requests/{id}/status."""

    def test_unknown_id_returns_404(self) -> None:
        resp = _client.get("/api/access-requests/nonexistent-id/status")
        self.assertEqual(resp.status_code, 404)

    def test_known_pending_request_returns_status(self) -> None:
        ar = _make_pending(name="Status Alice", ip="2.2.2.2")
        resp = _client.get(f"/api/access-requests/{ar.id}/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], ar.id)
        self.assertEqual(data["status"], "pending")

    def test_response_contains_only_id_and_status(self) -> None:
        """No PII (name, email, motive) in the public status endpoint."""
        ar = _make_pending(name="Private Petra", email="private@example.com", ip="2.2.3.3")
        resp = _client.get(f"/api/access-requests/{ar.id}/status")
        data = resp.json()
        self.assertNotIn("name", data)
        self.assertNotIn("email", data)
        self.assertNotIn("motive", data)
        self.assertNotIn("company", data)

    def test_approved_request_returns_approved_status(self) -> None:
        ar = _make_pending(name="Approved Alain", ip="2.2.4.4")
        ar.approve()
        _store.update(ar)
        resp = _client.get(f"/api/access-requests/{ar.id}/status")
        self.assertEqual(resp.json()["status"], "approved")


# ── GET /api/access-requests/{id}/decide ─────────────────────────────────────


class DecideEndpointTests(unittest.TestCase):
    """S4-3: GET /api/access-requests/{id}/decide?token=..."""

    def _decide(self, request_id: str, token: str) -> Any:
        return _client.get(
            f"/api/access-requests/{request_id}/decide",
            params={"token": token},
        )

    def test_missing_token_returns_422(self) -> None:
        ar = _make_pending(name="No Token", ip="3.0.0.1")
        resp = _client.get(f"/api/access-requests/{ar.id}/decide")
        self.assertEqual(resp.status_code, 422)

    def test_forged_token_returns_403(self) -> None:
        ar = _make_pending(name="Forge Victor", ip="3.0.0.2")
        resp = self._decide(ar.id, "totally.fake")
        self.assertEqual(resp.status_code, 403)

    def test_expired_token_returns_403(self) -> None:
        ar = _make_pending(name="Expired Edgar", ip="3.0.0.3")
        token = _sign_expired({"sub": "decide", "req": ar.id, "accept": 1})
        resp = self._decide(ar.id, token)
        self.assertEqual(resp.status_code, 403)

    def test_wrong_sub_in_token_returns_403(self) -> None:
        ar = _make_pending(name="Wrong Sub", ip="3.0.0.4")
        token = _sign({"sub": "session", "req": ar.id, "accept": 1})
        resp = self._decide(ar.id, token)
        self.assertEqual(resp.status_code, 403)

    def test_token_for_different_request_id_returns_403(self) -> None:
        ar = _make_pending(name="Mismatch Monica", ip="3.0.0.5")
        token = _sign({"sub": "decide", "req": "other-id", "accept": 1})
        resp = self._decide(ar.id, token)
        self.assertEqual(resp.status_code, 403)

    def test_approve_transitions_request_to_approved(self) -> None:
        ar = _make_pending(name="Approve Anna", ip="3.0.1.1")
        token = _sign({"sub": "decide", "req": ar.id, "accept": 1})
        resp = self._decide(ar.id, token)
        self.assertEqual(resp.status_code, 200)
        # HTML page is returned — just check it's not an error page.
        self.assertIn("approved", resp.text.lower())
        # Store reflects the transition.
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "approved")

    def test_reject_transitions_request_to_rejected(self) -> None:
        ar = _make_pending(name="Reject Robert", ip="3.0.1.2")
        token = _sign({"sub": "decide", "req": ar.id, "accept": 0})
        resp = self._decide(ar.id, token)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rejected", resp.text.lower())
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "rejected")

    def test_idempotent_second_approval_returns_200(self) -> None:
        """Calling decide twice for the same request must not error."""
        ar = _make_pending(name="Idempotent Ida", ip="3.0.2.1")
        token = _sign({"sub": "decide", "req": ar.id, "accept": 1})
        resp1 = self._decide(ar.id, token)
        resp2 = self._decide(ar.id, token)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("already decided", resp2.text.lower())

    def test_decide_unknown_id_returns_404(self) -> None:
        token = _sign({"sub": "decide", "req": "ghost-id", "accept": 1})
        resp = _client.get("/api/access-requests/ghost-id/decide", params={"token": token})
        self.assertEqual(resp.status_code, 404)


# ── POST /api/telegram/webhook ────────────────────────────────────────────────


class TelegramWebhookTests(unittest.TestCase):
    """S4-4: POST /api/telegram/webhook."""

    def _post(self, body: dict) -> Any:
        return _client.post("/api/telegram/webhook", json=body)

    def test_empty_body_returns_ok(self) -> None:
        resp = self._post({})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    def test_non_owner_callback_is_dropped_silently(self) -> None:
        ar = _make_pending(name="Tg Drop", ip="4.0.0.1")
        resp = self._post({
            "callback_query": {
                "from": {"id": 99998},  # not the owner
                "data": f"approve:{ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        # Request must NOT have been approved.
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "pending")

    def test_non_owner_message_is_dropped_silently(self) -> None:
        ar = _make_pending(name="Tg Msg Drop", ip="4.0.0.2")
        resp = self._post({
            "message": {
                "from": {"id": 12345},  # not the owner
                "text": f"/approve {ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "pending")

    def test_owner_approve_callback_transitions_to_approved(self) -> None:
        ar = _make_pending(name="Tg Approve", ip="4.0.1.1")
        resp = self._post({
            "callback_query": {
                "from": {"id": int(_OWNER_CHAT_ID)},
                "data": f"approve:{ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "approved")

    def test_owner_reject_callback_transitions_to_rejected(self) -> None:
        ar = _make_pending(name="Tg Reject", ip="4.0.1.2")
        resp = self._post({
            "callback_query": {
                "from": {"id": int(_OWNER_CHAT_ID)},
                "data": f"reject:{ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "rejected")

    def test_owner_approve_message_command_transitions_to_approved(self) -> None:
        ar = _make_pending(name="Tg Cmd Approve", ip="4.0.2.1")
        resp = self._post({
            "message": {
                "from": {"id": int(_OWNER_CHAT_ID)},
                "text": f"/approve {ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "approved")

    def test_owner_reject_message_command_transitions_to_rejected(self) -> None:
        ar = _make_pending(name="Tg Cmd Reject", ip="4.0.2.2")
        resp = self._post({
            "message": {
                "from": {"id": int(_OWNER_CHAT_ID)},
                "text": f"/reject {ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        updated = _store.get(ar.id)
        self.assertEqual(str(updated.status), "rejected")

    def test_already_approved_callback_does_not_error(self) -> None:
        ar = _make_pending(name="Tg Idempotent", ip="4.0.3.1")
        ar.approve()
        _store.update(ar)
        resp = self._post({
            "callback_query": {
                "from": {"id": int(_OWNER_CHAT_ID)},
                "data": f"approve:{ar.id}",
            }
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    def test_unknown_request_id_in_callback_returns_ok(self) -> None:
        resp = self._post({
            "callback_query": {
                "from": {"id": int(_OWNER_CHAT_ID)},
                "data": "approve:ghost-id",
            }
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])


# ── POST /api/admin/login ─────────────────────────────────────────────────────


class AdminLoginTests(unittest.TestCase):
    """S4-5: POST /api/admin/login."""

    def test_always_returns_sent_true_for_unknown_email(self) -> None:
        resp = _client.post("/api/admin/login", json={"email": "nobody@example.com"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["sent"])

    def test_always_returns_sent_true_for_owner_email(self) -> None:
        resp = _client.post("/api/admin/login", json={"email": _OWNER_EMAIL})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["sent"])

    def test_response_body_does_not_reveal_email_match(self) -> None:
        """Both owner and non-owner must get identical responses (oracle protection)."""
        r_owner = _client.post("/api/admin/login", json={"email": _OWNER_EMAIL})
        r_other = _client.post("/api/admin/login", json={"email": "spy@example.com"})
        self.assertEqual(r_owner.json(), r_other.json())
        self.assertEqual(r_owner.status_code, r_other.status_code)


# ── GET /api/admin/session/{token} ────────────────────────────────────────────


class AdminSessionTests(unittest.TestCase):
    """S4-6: GET /api/admin/session/{token}."""

    def test_forged_token_returns_401(self) -> None:
        resp = _client.get("/api/admin/session/forged.token")
        self.assertEqual(resp.status_code, 401)

    def test_expired_token_returns_401(self) -> None:
        token = _sign_expired({"sub": "admin-magic"})
        resp = _client.get(f"/api/admin/session/{token}")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_sub_returns_401(self) -> None:
        token = _sign({"sub": "session"})
        resp = _client.get(f"/api/admin/session/{token}")
        self.assertEqual(resp.status_code, 401)

    def test_valid_magic_token_returns_session_token(self) -> None:
        token = _sign({"sub": "admin-magic"})
        resp = _client.get(f"/api/admin/session/{token}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("session_token", data)
        self.assertTrue(data["session_token"])

    def test_returned_session_token_is_verifiable(self) -> None:
        from cv_critic_agent.security.crypto import verify_token

        magic_token = _sign({"sub": "admin-magic"})
        session_token = _client.get(f"/api/admin/session/{magic_token}").json()["session_token"]
        payload = verify_token(session_token, _HMAC_KEY.encode())
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "admin-session")


# ── GET /api/admin/requests ───────────────────────────────────────────────────


class AdminRequestsListTests(unittest.TestCase):
    """S4-7: GET /api/admin/requests (requires admin session)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Get a valid admin session token.
        magic = _sign({"sub": "admin-magic"})
        cls._session = _client.get(f"/api/admin/session/{magic}").json()["session_token"]

    def test_no_session_returns_401(self) -> None:
        resp = _client.get("/api/admin/requests")
        self.assertEqual(resp.status_code, 401)

    def test_forged_session_returns_401(self) -> None:
        resp = _client.get(
            "/api/admin/requests",
            headers={"X-Admin-Session": "forged.token"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_valid_session_returns_requests_list(self) -> None:
        resp = _client.get(
            "/api/admin/requests",
            headers={"X-Admin-Session": self._session},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("requests", data)
        self.assertIsInstance(data["requests"], list)

    def test_status_filter_returns_only_matching(self) -> None:
        ar = _make_pending(name="Filter Pending", ip="5.0.1.1")
        resp = _client.get(
            "/api/admin/requests",
            params={"status": "pending"},
            headers={"X-Admin-Session": self._session},
        )
        self.assertEqual(resp.status_code, 200)
        statuses = {r["status"] for r in resp.json()["requests"]}
        self.assertEqual(statuses, {"pending"})

    def test_invalid_status_filter_returns_400(self) -> None:
        resp = _client.get(
            "/api/admin/requests",
            params={"status": "invalid_status_value"},
            headers={"X-Admin-Session": self._session},
        )
        self.assertEqual(resp.status_code, 400)

    def test_response_includes_pii_for_admin(self) -> None:
        """Admin listing must expose PII (unlike the public status endpoint)."""
        ar = _make_pending(name="PII Petra", email="pii@example.com", ip="5.0.2.1")
        resp = _client.get(
            "/api/admin/requests",
            headers={"X-Admin-Session": self._session},
        )
        all_names = [r["name"] for r in resp.json()["requests"]]
        self.assertIn("PII Petra", all_names)


# ── PATCH /api/admin/requests/{id} ────────────────────────────────────────────


class AdminDecideTests(unittest.TestCase):
    """S4-8: PATCH /api/admin/requests/{id} (approve / reject / revoke)."""

    @classmethod
    def setUpClass(cls) -> None:
        magic = _sign({"sub": "admin-magic"})
        cls._session = _client.get(f"/api/admin/session/{magic}").json()["session_token"]

    def _patch(self, request_id: str, action: str) -> Any:
        return _client.patch(
            f"/api/admin/requests/{request_id}",
            json={"action": action},
            headers={"X-Admin-Session": self._session},
        )

    def test_no_session_returns_401(self) -> None:
        ar = _make_pending(name="Admin Auth", ip="6.0.0.1")
        resp = _client.patch(f"/api/admin/requests/{ar.id}", json={"action": "approve"})
        self.assertEqual(resp.status_code, 401)

    def test_unknown_request_id_returns_404(self) -> None:
        resp = self._patch("ghost-id", "approve")
        self.assertEqual(resp.status_code, 404)

    def test_unknown_action_returns_400(self) -> None:
        ar = _make_pending(name="Bad Action", ip="6.0.0.2")
        resp = self._patch(ar.id, "teleport")
        self.assertEqual(resp.status_code, 400)

    def test_approve_transitions_to_approved(self) -> None:
        ar = _make_pending(name="Admin Approve", ip="6.0.1.1")
        resp = self._patch(ar.id, "approve")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "approved")
        self.assertEqual(str(_store.get(ar.id).status), "approved")

    def test_reject_transitions_to_rejected(self) -> None:
        ar = _make_pending(name="Admin Reject", ip="6.0.1.2")
        resp = self._patch(ar.id, "reject")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "rejected")

    def test_revoke_approved_transitions_to_revoked(self) -> None:
        ar = _make_pending(name="Admin Revoke", ip="6.0.1.3")
        ar.approve()
        _store.update(ar)
        resp = self._patch(ar.id, "revoke")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "revoked")

    def test_double_approve_returns_409(self) -> None:
        ar = _make_pending(name="Double Approve", ip="6.0.2.1")
        self._patch(ar.id, "approve")
        resp = self._patch(ar.id, "approve")
        self.assertEqual(resp.status_code, 409)

    def test_reject_already_approved_returns_409(self) -> None:
        ar = _make_pending(name="Reject Approved", ip="6.0.2.2")
        ar.approve()
        _store.update(ar)
        resp = self._patch(ar.id, "reject")
        self.assertEqual(resp.status_code, 409)


if __name__ == "__main__":
    unittest.main()
