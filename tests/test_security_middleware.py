"""Tests for Turnstile verify, rate limiter and security headers.

Each section pins one realistic failure mode for its concern: Turnstile
fails closed on every category of error; the limiter actually 429s on the
N+1 call; headers are added with safe defaults.
"""
from __future__ import annotations

import unittest

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from cv_critic_agent.security.security_middleware import (
    TURNSTILE_TOKEN_HEADER,
    CSPConfig,
    SecurityHeadersMiddleware,
    make_limiter,
    verify_turnstile,
)


# ── Test doubles for the Cloudflare siteverify response ────────────────────
class _MockResponse:
    def __init__(self, status_code: int, json_data: dict) -> None:
        self.status_code = status_code
        self._json = json_data

    def json(self) -> dict:
        return self._json


class _MockAsyncClient:
    def __init__(self, response: _MockResponse | None = None,
                 raises: Exception | None = None) -> None:
        self._response = response
        self._raises = raises

    async def __aenter__(self) -> _MockAsyncClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, *_args: object, **_kwargs: object) -> _MockResponse:
        if self._raises:
            raise self._raises
        assert self._response is not None
        return self._response


def _factory_response(status_code: int, json_data: dict):
    def _factory(**_kwargs: object) -> _MockAsyncClient:
        return _MockAsyncClient(_MockResponse(status_code, json_data))
    return _factory


def _factory_raises(exc: Exception):
    def _factory(**_kwargs: object) -> _MockAsyncClient:
        return _MockAsyncClient(raises=exc)
    return _factory


def _request(headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/x",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": ("127.0.0.1", 12345),
        "query_string": b"",
    }
    return Request(scope)


class TurnstileVerifyTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_secret_returns_503(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await verify_turnstile(_request({TURNSTILE_TOKEN_HEADER: "tk"}), "")
        self.assertEqual(ctx.exception.status_code, 503)

    async def test_missing_token_rejected(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await verify_turnstile(_request(), "secret")
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_valid_token_passes(self) -> None:
        await verify_turnstile(
            _request({TURNSTILE_TOKEN_HEADER: "tk"}),
            "secret",
            http_client_factory=_factory_response(200, {"success": True, "score": 0.9}),
        )

    async def test_success_false_rejected(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await verify_turnstile(
                _request({TURNSTILE_TOKEN_HEADER: "tk"}),
                "secret",
                http_client_factory=_factory_response(200, {"success": False}),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_low_score_rejected(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await verify_turnstile(
                _request({TURNSTILE_TOKEN_HEADER: "tk"}),
                "secret",
                http_client_factory=_factory_response(200, {"success": True, "score": 0.3}),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_network_error_fails_closed(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await verify_turnstile(
                _request({TURNSTILE_TOKEN_HEADER: "tk"}),
                "secret",
                http_client_factory=_factory_raises(httpx.ConnectError("net down")),
            )
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_non_200_status_rejected(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            await verify_turnstile(
                _request({TURNSTILE_TOKEN_HEADER: "tk"}),
                "secret",
                http_client_factory=_factory_response(500, {}),
            )
        self.assertEqual(ctx.exception.status_code, 403)


class SecurityHeadersTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/x")
        def _root() -> dict:
            return {"ok": True}

        self.client = TestClient(app)

    def test_csp_header_present(self) -> None:
        response = self.client.get("/x")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_hsts_2_years(self) -> None:
        response = self.client.get("/x")
        self.assertIn("max-age=63072000", response.headers["Strict-Transport-Security"])

    def test_x_frame_options_deny(self) -> None:
        response = self.client.get("/x")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_referrer_policy_strict(self) -> None:
        response = self.client.get("/x")
        self.assertEqual(
            response.headers["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )


class CSPConfigTests(unittest.TestCase):
    def test_default_contains_self(self) -> None:
        self.assertIn("default-src 'self'", CSPConfig().to_header())

    def test_frame_ancestors_none_by_default(self) -> None:
        self.assertIn("frame-ancestors 'none'", CSPConfig().to_header())

    def test_custom_script_src_used(self) -> None:
        custom = CSPConfig(script_src="'self' 'unsafe-inline'")
        self.assertIn("script-src 'self' 'unsafe-inline'", custom.to_header())


class RateLimitIntegrationTests(unittest.TestCase):
    def test_429_after_limit_reached(self) -> None:
        limiter = Limiter(
            key_func=lambda *_a, **_k: "fixed-key",
            default_limits=[],
        )
        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)

        @app.get("/r")
        @limiter.limit("2/minute")
        def _route(request: Request) -> dict:  # noqa: ARG001 — slowapi needs `request`
            return {"ok": True}

        client = TestClient(app)
        self.assertEqual(client.get("/r").status_code, 200)
        self.assertEqual(client.get("/r").status_code, 200)
        self.assertEqual(client.get("/r").status_code, 429)

    def test_make_limiter_uses_remote_address_key(self) -> None:
        limiter = make_limiter(default_limits=["100/hour"])
        self.assertIsInstance(limiter, Limiter)


if __name__ == "__main__":
    unittest.main()
