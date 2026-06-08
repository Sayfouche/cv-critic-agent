"""Sprint 5 — POST /api/runs real-mode gate.

Verifies the new session_token + budget-tracker behaviour:

- Mock runs need no auth (unchanged).
- Real runs require a valid session_token (HMAC, sub=session, exp).
- Real runs are IP-bound after the first call.
- Real runs cost one slot from the requester's runs_quota.
- If the daily budget cap is hit, real runs degrade silently to mock —
  no slot is consumed and the response has ``degraded: true``.
"""
from __future__ import annotations

import base64
import hmac as hmac_mod
import json
import os
import shutil
import tempfile
import time
import unittest
from hashlib import sha256
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet

# ── module-level test fixtures ────────────────────────────────────────────────

_HMAC_KEY = "test-hmac-secret-key-sprint-5-ok"
_FERNET_KEY = Fernet.generate_key().decode()
_DAILY_CAP = 10_000

_client = None
_client_ctx = None
_store = None
_budget_dir: str | None = None
_ar_dir: str | None = None
_env_patcher = None


def setUpModule() -> None:
    global _client, _client_ctx, _store, _budget_dir, _ar_dir, _env_patcher

    _ar_dir = tempfile.mkdtemp(prefix="cv-critic-runs-ar-")
    _budget_dir = tempfile.mkdtemp(prefix="cv-critic-runs-budget-")
    _env_patcher = mock.patch.dict(
        os.environ,
        {
            "HMAC_KEY": _HMAC_KEY,
            "FERNET_KEY": _FERNET_KEY,
            "ACCESS_REQUESTS_DIR": _ar_dir,
            "BUDGET_DIR": _budget_dir,
            "MAX_TOKENS_PER_DAY": str(_DAILY_CAP),
        },
    )
    _env_patcher.start()

    from fastapi.testclient import TestClient

    from cv_critic_agent.api import app

    _client_ctx = TestClient(app)
    _client = _client_ctx.__enter__()
    _store = app.state.ar_store


def tearDownModule() -> None:
    global _env_patcher, _ar_dir, _budget_dir, _client_ctx
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
    if _ar_dir:
        shutil.rmtree(_ar_dir, ignore_errors=True)
    if _budget_dir:
        shutil.rmtree(_budget_dir, ignore_errors=True)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sign(payload: dict, ttl: int = 3600) -> str:
    from cv_critic_agent.security.crypto import sign_token

    return sign_token(payload, _HMAC_KEY.encode(), ttl)


def _sign_expired(payload: dict) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) - 1
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    sig = base64.urlsafe_b64encode(
        hmac_mod.new(_HMAC_KEY.encode(), encoded.encode("ascii"), sha256).digest()
    ).rstrip(b"=").decode("ascii")
    return f"{encoded}.{sig}"


def _seed_approved(ip: str = "1.1.1.1", quota: int = 3):
    from cv_critic_agent.access_requests.models import AccessRequest

    req = AccessRequest.new(
        name="Alice",
        company="ACME",
        email="alice@example.com",
        motive="test",
        requester_ip=ip,
    )
    req.runs_quota = quota
    req.approve()
    _store.create(req)
    return req


def _reset_budget() -> None:
    from cv_critic_agent.api import app

    app.state.budget_tracker.add_tokens(0)
    # Easiest reset: nuke the day file.
    import datetime as dt

    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    path = Path(_budget_dir) / f"{today}.json"
    if path.exists():
        path.unlink()


# ── Mock runs (still public) ──────────────────────────────────────────────────


class MockRunsAreFreeTests(unittest.TestCase):
    def test_mock_run_does_not_require_session_token(self) -> None:
        response = _client.post("/api/runs", json={"mock": True})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["mock"])
        self.assertFalse(body["degraded"])

    def test_mock_run_ignores_session_token_header(self) -> None:
        response = _client.post(
            "/api/runs",
            json={"mock": True},
            headers={"X-Session-Token": "garbage"},
        )
        self.assertEqual(response.status_code, 200)


# ── Token-level failures ──────────────────────────────────────────────────────


class TokenFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_budget()

    def test_real_run_without_session_token_returns_401(self) -> None:
        response = _client.post("/api/runs", json={"mock": False})
        self.assertEqual(response.status_code, 401)

    def test_real_run_with_forged_signature_returns_401(self) -> None:
        ar = _seed_approved()
        good = _sign({"sub": "session", "req": ar.id})
        encoded, _sig = good.split(".", 1)
        forged = f"{encoded}.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        response = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": forged, "X-Forwarded-For": "1.1.1.1"},
        )
        self.assertEqual(response.status_code, 401)

    def test_real_run_with_expired_token_returns_401(self) -> None:
        ar = _seed_approved()
        token = _sign_expired({"sub": "session", "req": ar.id})
        response = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "1.1.1.1"},
        )
        self.assertEqual(response.status_code, 401)

    def test_real_run_with_wrong_sub_returns_401(self) -> None:
        ar = _seed_approved()
        token = _sign({"sub": "decide", "req": ar.id})
        response = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "1.1.1.1"},
        )
        self.assertEqual(response.status_code, 401)

    def test_real_run_with_unknown_req_returns_403(self) -> None:
        token = _sign({"sub": "session", "req": "nonexistent"})
        response = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "1.1.1.1"},
        )
        self.assertEqual(response.status_code, 403)


# ── IP binding ────────────────────────────────────────────────────────────────


class IpBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_budget()

    def test_real_run_from_different_ip_returns_403(self) -> None:
        ar = _seed_approved()
        token = _sign({"sub": "session", "req": ar.id})
        # First call binds 1.1.1.1
        first = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "1.1.1.1"},
        )
        self.assertEqual(first.status_code, 200)
        # Second call from 2.2.2.2 must be rejected.
        second = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "2.2.2.2"},
        )
        self.assertEqual(second.status_code, 403)


# ── Quota ─────────────────────────────────────────────────────────────────────


class QuotaTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_budget()

    def test_quota_exhausted_returns_403(self) -> None:
        ar = _seed_approved(quota=2)
        token = _sign({"sub": "session", "req": ar.id})
        ip = "5.5.5.5"
        # Two valid calls (consume slots 1 and 2).
        for _ in range(2):
            r = _client.post(
                "/api/runs",
                json={"mock": False},
                headers={"X-Session-Token": token, "X-Forwarded-For": ip},
            )
            self.assertEqual(r.status_code, 200)
        # Third must fail.
        r = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": ip},
        )
        self.assertEqual(r.status_code, 403)


# ── Budget cap → graceful degradation ─────────────────────────────────────────


class BudgetCapTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_budget()

    def test_budget_cap_degrades_to_mock(self) -> None:
        from cv_critic_agent.api import app

        # Fill the day's budget past cap.
        app.state.budget_tracker.add_tokens(_DAILY_CAP + 1)
        ar = _seed_approved()
        token = _sign({"sub": "session", "req": ar.id})

        response = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "1.1.1.1"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["mock"])
        self.assertTrue(body["degraded"])

        # Critically: no slot was consumed.
        reloaded = _store.get(ar.id)
        self.assertEqual(reloaded.runs_used, 0)
        self.assertIsNone(reloaded.session_ip_binding)


# ── Happy path ────────────────────────────────────────────────────────────────


class HappyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_budget()

    def test_first_real_run_binds_ip_and_consumes_slot(self) -> None:
        ar = _seed_approved()
        token = _sign({"sub": "session", "req": ar.id})

        response = _client.post(
            "/api/runs",
            json={"mock": False},
            headers={"X-Session-Token": token, "X-Forwarded-For": "9.9.9.9"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["mock"])
        self.assertFalse(body["degraded"])

        reloaded = _store.get(ar.id)
        self.assertEqual(reloaded.runs_used, 1)
        self.assertEqual(reloaded.session_ip_binding, "9.9.9.9")

    def test_token_via_query_param_also_works(self) -> None:
        ar = _seed_approved()
        token = _sign({"sub": "session", "req": ar.id})

        response = _client.post(
            f"/api/runs?token={token}",
            json={"mock": False},
            headers={"X-Forwarded-For": "9.9.9.9"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["mock"])


if __name__ == "__main__":
    unittest.main()
