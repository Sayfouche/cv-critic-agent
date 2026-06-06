"""Cross-module integration test: the full security chain on a tiny FastAPI app.

Each module has its own unit tests (test_crypto, test_pii, test_logging_filter,
test_security_middleware). This file proves the pieces compose correctly when
wired up the way the real `api.py` will do it: Turnstile dep → rate limit
decorator → handler → response with security headers, and logs masked along
the way.

A regression here means a sprint-1 contract drifted in a way unit tests
couldn't catch.
"""
from __future__ import annotations

import io
import logging
import unittest

from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from cv_critic_agent.security import (
    EmailMaskingFilter,
    SecurityHeadersMiddleware,
    decrypt_pii,
    encrypt_pii,
    sign_token,
    verify_token,
    verify_turnstile,
)
from cv_critic_agent.security.security_middleware import TURNSTILE_TOKEN_HEADER

TURNSTILE_SECRET = "test-secret"
HMAC_SECRET = b"\x42" * 32
FERNET_KEY = Fernet.generate_key()


# ── Fake Turnstile siteverify so the test never hits Cloudflare ──────────────
class _MockResp:
    status_code = 200

    def json(self) -> dict:
        return {"success": True, "score": 0.95}


class _MockClient:
    async def __aenter__(self) -> _MockClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, *_args: object, **_kwargs: object) -> _MockResp:
        return _MockResp()


def _factory_always_ok(**_kwargs: object) -> _MockClient:
    return _MockClient()


# ── App under test: composes every Sprint-1 primitive ────────────────────────
def _build_app() -> FastAPI:
    app = FastAPI()
    limiter = Limiter(
        key_func=lambda *_a, **_k: "fixed-key",
        default_limits=[],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    async def turnstile_dep(request: Request) -> None:
        await verify_turnstile(
            request,
            TURNSTILE_SECRET,
            http_client_factory=_factory_always_ok,
        )

    @app.post("/submit", dependencies=[Depends(turnstile_dep)])
    @limiter.limit("2/minute")
    def submit(request: Request) -> dict:  # noqa: ARG001 — slowapi inspects signature
        # Demonstrate the chain : a token is issued + the email is masked when logged.
        token = sign_token({"role": "requester"}, HMAC_SECRET, ttl_seconds=60)
        logging.getLogger("chain-test").info("submitted by alice@example.com")
        return {"token": token}

    return app


class SecurityChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _build_app()
        self.client = TestClient(self.app)
        # Capture chain-test logger output and install the masking filter on it.
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.addFilter(EmailMaskingFilter())
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger = logging.getLogger("chain-test")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(self.handler)

    def tearDown(self) -> None:
        self.logger.handlers.clear()

    def _good_request(self) -> dict:
        return {"headers": {TURNSTILE_TOKEN_HEADER: "tk"}}

    def test_full_chain_accepts_valid_request(self) -> None:
        response = self.client.post("/submit", **self._good_request())
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]
        payload = verify_token(token, HMAC_SECRET)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["role"], "requester")

    def test_missing_turnstile_token_blocks_at_step_one(self) -> None:
        response = self.client.post("/submit")
        # 403 from Turnstile dep — the route was never reached.
        self.assertEqual(response.status_code, 403)
        # And no token was logged for this attempt.
        self.assertEqual(self.stream.getvalue(), "")

    def test_rate_limit_kicks_in_after_quota(self) -> None:
        self.client.post("/submit", **self._good_request())
        self.client.post("/submit", **self._good_request())
        third = self.client.post("/submit", **self._good_request())
        self.assertEqual(third.status_code, 429)

    def test_security_headers_present_on_every_response(self) -> None:
        # Valid request: handler reached.
        ok = self.client.post("/submit", **self._good_request())
        for header in (
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        ):
            with self.subTest(header=header, response="200"):
                self.assertIn(header, ok.headers)
        # Rejected request: still gets headers (no information leak via missing headers).
        rejected = self.client.post("/submit")
        with self.subTest(header="Content-Security-Policy", response="403"):
            self.assertIn("Content-Security-Policy", rejected.headers)

    def test_handler_log_is_masked_in_chain(self) -> None:
        self.client.post("/submit", **self._good_request())
        log_output = self.stream.getvalue()
        self.assertIn("a****@example.com", log_output)
        self.assertNotIn("alice@example.com", log_output)

    def test_pii_round_trip_in_realistic_flow(self) -> None:
        # Simulate storing the requester email at rest then reading it back.
        ciphertext = encrypt_pii("bob@example.org", FERNET_KEY)
        self.assertNotIn("bob", ciphertext)
        self.assertEqual(decrypt_pii(ciphertext, FERNET_KEY), "bob@example.org")


if __name__ == "__main__":
    unittest.main()
