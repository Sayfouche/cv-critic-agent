"""Security middlewares: Turnstile verification, rate limiting, security headers.

Three independent concerns bundled in one module because they all decorate
the same FastAPI app at startup. No shared state between them.

Turnstile (Cloudflare's lightweight captcha):
    Verify on every public form submission. Client sends a token header; we
    POST to siteverify with our server-side secret. We fail closed on any
    error — missing token, network problem, score below 0.5, success=false.

Rate limiting (slowapi):
    Configured at module level, attached to the FastAPI app. Default limit
    applies app-wide; per-endpoint `@limiter.limit("3/hour")` can tighten.
    In-memory store matches our single-instance Render deployment.

Security headers:
    Middleware that adds OWASP-recommended headers on every response. Safe
    defaults; CSP overrideable via CSPConfig for the parts the UI needs.

This module never reads the environment. Callers pass `secret` explicitly so
rotation and testing stay easy.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_TOKEN_HEADER = "cf-turnstile-response"
TURNSTILE_MIN_SCORE = 0.5
TURNSTILE_TIMEOUT_SECONDS = 5.0


# ─── Turnstile ────────────────────────────────────────────────────────────────
async def verify_turnstile(
    request: Request,
    secret: str,
    *,
    http_client_factory: Callable[..., Any] | None = None,
) -> None:
    """Raise HTTPException unless the request carries a valid Turnstile token.

    `http_client_factory` is injectable for tests; in prod it defaults to
    `httpx.AsyncClient`. Network errors fail closed (403, never 5xx) so the
    caller does not need to think about partial outages.
    """
    if not secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Captcha not configured on this server.",
        )
    token = request.headers.get(TURNSTILE_TOKEN_HEADER)
    if not token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing captcha token.")

    factory = http_client_factory or httpx.AsyncClient
    try:
        async with factory(timeout=TURNSTILE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": secret,
                    "response": token,
                    "remoteip": get_remote_address(request),
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Captcha verification failed."
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Captcha verification failed.")
    payload = response.json()
    if not payload.get("success"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Captcha rejected.")
    score = payload.get("score")
    if isinstance(score, (int, float)) and score < TURNSTILE_MIN_SCORE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Captcha score too low.")


# ─── Rate limit ───────────────────────────────────────────────────────────────
def make_limiter(default_limits: list[str] | None = None) -> Limiter:
    """Build a slowapi limiter keyed on the client IP.

    `default_limits` set an app-wide ceiling. Per-route decorators may
    override or tighten with `@limiter.limit("3/hour")`.
    """
    return Limiter(
        key_func=get_remote_address,
        default_limits=default_limits or ["30/day"],
    )


# ─── Security headers ─────────────────────────────────────────────────────────
@dataclass
class CSPConfig:
    """Minimal Content-Security-Policy — overrideable per deployment."""

    default_src: str = "'self'"
    img_src: str = "'self' data:"
    style_src: str = "'self' 'unsafe-inline'"
    script_src: str = "'self'"
    connect_src: str = "'self'"
    frame_ancestors: str = "'none'"

    def to_header(self) -> str:
        return (
            f"default-src {self.default_src}; "
            f"img-src {self.img_src}; "
            f"style-src {self.style_src}; "
            f"script-src {self.script_src}; "
            f"connect-src {self.connect_src}; "
            f"frame-ancestors {self.frame_ancestors}"
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended headers to every response."""

    def __init__(self, app, csp: CSPConfig | None = None) -> None:
        super().__init__(app)
        self.csp = csp or CSPConfig()

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", self.csp.to_header())
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        return response
