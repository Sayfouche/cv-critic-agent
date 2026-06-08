"""Module-level slowapi Limiter singleton.

Both the access-request router (for @limiter.limit decorators) and api.py
(which sets app.state.limiter so slowapi can find it at request time) must
share the *same* object. A module-level singleton satisfies this requirement.

Key function reads X-Forwarded-For so the real IP is used when the server
sits behind a reverse-proxy (Cloudflare → Render). Tests can inject distinct
IPs via this header to isolate test runs from each other's rate buckets.

Usage in api.py:
    from cv_critic_agent.security.limiter import limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Usage in a router:
    from cv_critic_agent.security.limiter import limiter
    @router.post("/foo")
    @limiter.limit("3/hour")
    async def foo(request: Request, ...): ...
"""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_ip(request: Request) -> str:
    """Return the real client IP, preferring X-Forwarded-For over socket addr.

    In production (behind Cloudflare → Render), the first entry of
    X-Forwarded-For is the original client IP. In tests, individual test
    methods inject their own IPs via this header to prevent cross-test
    rate-limit bleeding.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
