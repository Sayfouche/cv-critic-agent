"""Cron-triggered maintenance endpoint.

A daily external trigger (Render cron, GitHub Actions, etc.) calls
``POST /api/cron/cleanup`` with the ``X-Cleanup-Secret`` header to:

1. Drop access-request files past their TTL (pending: 7 d, decided: 90 d).
2. Delete per-day budget JSON files older than 90 days.

The endpoint is idempotent (safe to fire multiple times per day) and
returns the count of items removed so the caller can graph the eviction
rate. Auth uses a constant-time string compare to avoid timing oracles.
"""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/api/cron", tags=["cron"])


_BUDGET_RETENTION_DAYS = 90


@router.post("/cleanup")
async def cleanup(
    request: Request,
    x_cleanup_secret: str | None = Header(default=None, alias="X-Cleanup-Secret"),
) -> dict[str, Any]:
    expected = getattr(request.app.state, "cleanup_secret", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Cleanup is disabled on this server.")
    if not x_cleanup_secret or not hmac.compare_digest(x_cleanup_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid cleanup secret.")

    ar_store = getattr(request.app.state, "ar_store", None)
    budget_tracker = getattr(request.app.state, "budget_tracker", None)

    access_requests_purged = ar_store.cleanup_expired() if ar_store is not None else 0
    budget_files_purged = (
        budget_tracker.cleanup_old_days(retain_days=_BUDGET_RETENTION_DAYS)
        if budget_tracker is not None
        else 0
    )
    return {
        "access_requests_purged": access_requests_purged,
        "budget_files_purged": budget_files_purged,
    }
