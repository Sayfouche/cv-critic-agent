"""FastAPI router: admin magic-link auth + access-request management.

Endpoints
---------
POST  /api/admin/login
    Accepts {email}. If email matches OWNER_EMAIL, sends a magic link to
    the owner. Always returns {"sent": true} (oracle protection).

GET   /api/admin/session/{token}
    Verifies the magic-link token and issues a 24-hour admin session token.
    Returns {"session_token": "..."} — the UI stores this and sends it as
    the X-Admin-Session header on subsequent requests.

GET   /api/admin/requests?status=<filter>
    Lists access requests. Requires X-Admin-Session header (or
    admin_session cookie). Optional `status` query param filters by status
    value; omit for all.

PATCH /api/admin/requests/{request_id}
    Approve / reject / revoke a single request. Body: {"action": "approve"|
    "reject"|"revoke"}. Requires admin session. Returns the updated status.

Security
--------
- Magic-link token TTL: 30 minutes. Not one-time-use (the window is short
  enough; true OTU would require a denylist which adds complexity).
- Admin session token TTL: 24 hours. Stateless HMAC; revocation requires
  key rotation.
- All admin endpoints return 401 for unauthenticated requests.

State dependencies (set by api.py lifespan, read via app.state):
    hmac_secret            bytes
    ar_store               AccessRequestStore | None
    owner_email            str
    resend_api_key         str
    resend_from            str
    ui_url                 str
    notifier_http_factory  Callable | None
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from cv_critic_agent.access_requests.models import AccessRequestStatus, InvalidTransition
from cv_critic_agent.access_requests.store import AccessRequestStore
from cv_critic_agent.notifier.email import (
    send_admin_magic_link,
    send_requester_approved,
    send_requester_rejected,
)
from cv_critic_agent.security.crypto import sign_token, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_MAGIC_LINK_TTL = 30 * 60   # 30 minutes
_SESSION_TTL = 24 * 3_600   # 24 hours
_SESSION_TOKEN_TTL = 24 * 3_600


# ── auth helpers ─────────────────────────────────────────────────────────────

def _require_admin_session(request: Request) -> None:
    """Raise 401 unless the request carries a valid admin session token."""
    hmac_secret: bytes = getattr(request.app.state, "hmac_secret", b"")
    # Accept from header first, then cookie (for browser-based admin panel).
    raw = (
        request.headers.get("X-Admin-Session")
        or request.cookies.get("admin_session")
    )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session required.",
        )
    payload = verify_token(raw, hmac_secret)
    if payload is None or payload.get("sub") != "admin-session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session.",
        )


def _get_store(request: Request) -> AccessRequestStore:
    store: AccessRequestStore | None = getattr(request.app.state, "ar_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access gate not configured on this server.",
        )
    return store


# ── endpoints ────────────────────────────────────────────────────────────────

class AdminLoginBody(BaseModel):
    email: str


@router.post("/login")
async def admin_login(body: AdminLoginBody, request: Request) -> dict[str, bool]:
    """Send a magic-link email to the owner. Always returns {"sent": true}."""
    owner_email: str = getattr(request.app.state, "owner_email", "")
    hmac_secret: bytes = getattr(request.app.state, "hmac_secret", b"")
    base_url: str = getattr(request.app.state, "base_url", "").rstrip("/")
    resend_key: str = getattr(request.app.state, "resend_api_key", "")
    resend_from: str = getattr(request.app.state, "resend_from", "")
    notifier_factory = getattr(request.app.state, "notifier_http_factory", None)

    if owner_email and body.email == owner_email and resend_key:
        token = sign_token({"sub": "admin-magic"}, hmac_secret, _MAGIC_LINK_TTL)
        magic_url = f"{base_url}/api/admin/session/{token}"
        try:
            await send_admin_magic_link(
                api_key=resend_key,
                from_address=resend_from,
                to_address=owner_email,
                magic_url=magic_url,
                http_client_factory=notifier_factory,
            )
        except Exception:
            logger.exception("Admin magic link email failed")

    # Always return "sent" — never reveal whether the email matched.
    return {"sent": True}


@router.get("/session/{token}")
async def admin_session(token: str, request: Request) -> dict[str, str]:
    """Redeem a magic-link token and return a 24-hour admin session token."""
    hmac_secret: bytes = getattr(request.app.state, "hmac_secret", b"")
    payload = verify_token(token, hmac_secret)
    if payload is None or payload.get("sub") != "admin-magic":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link.",
        )
    session_token = sign_token({"sub": "admin-session"}, hmac_secret, _SESSION_TTL)
    return {"session_token": session_token}


@router.get("/requests")
async def list_requests(
    request: Request,
    filter_status: str | None = Query(default=None, alias="status"),
) -> dict[str, Any]:
    """List access requests. Requires X-Admin-Session header or admin_session cookie."""
    _require_admin_session(request)
    store = _get_store(request)

    if filter_status is not None:
        try:
            target_status = AccessRequestStatus(filter_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown status value: {filter_status!r}",
            )
        requests_list = store.list_by_status(target_status)
    else:
        # All non-expired requests across every status.
        requests_list = []
        for s in AccessRequestStatus:
            requests_list.extend(store.list_by_status(s))
        requests_list.sort(key=lambda r: r.created_at, reverse=True)

    return {
        "requests": [
            {
                "id": r.id,
                "name": r.name,
                "company": r.company,
                "email": r.email,
                "motive": r.motive,
                "status": str(r.status),
                "created_at": r.created_at,
                "decided_at": r.decided_at,
                "runs_used": r.runs_used,
                "runs_quota": r.runs_quota,
            }
            for r in requests_list
        ]
    }


class AdminActionBody(BaseModel):
    action: str  # "approve" | "reject" | "revoke"


@router.patch("/requests/{request_id}")
async def admin_decide(
    request_id: str,
    body: AdminActionBody,
    request: Request,
) -> dict[str, Any]:
    """Apply approve / reject / revoke to a single request."""
    _require_admin_session(request)
    store = _get_store(request)

    ar = store.get(request_id)
    if ar is None:
        raise HTTPException(status_code=404, detail="Access request not found.")

    hmac_secret: bytes = getattr(request.app.state, "hmac_secret", b"")
    resend_key: str = getattr(request.app.state, "resend_api_key", "")
    resend_from: str = getattr(request.app.state, "resend_from", "")
    ui_url: str = getattr(request.app.state, "ui_url", "").rstrip("/")
    notifier_factory = getattr(request.app.state, "notifier_http_factory", None)

    action = body.action.lower()
    if action == "approve":
        try:
            ar.approve()
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        store.update(ar)
        if resend_key and ar.email:
            session_token = sign_token(
                {"sub": "session", "req": request_id},
                hmac_secret,
                _SESSION_TOKEN_TTL,
            )
            session_url = f"{ui_url}/access-granted/{session_token}"
            try:
                await send_requester_approved(
                    api_key=resend_key,
                    from_address=resend_from,
                    to_address=ar.email,
                    requester_name=ar.name,
                    session_url=session_url,
                    runs_quota=ar.runs_quota,
                    session_expires_in_hours=24,
                    http_client_factory=notifier_factory,
                )
            except Exception:
                logger.exception("Admin approval email failed for %s", request_id)

    elif action == "reject":
        try:
            ar.reject()
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        store.update(ar)
        if resend_key and ar.email:
            try:
                await send_requester_rejected(
                    api_key=resend_key,
                    from_address=resend_from,
                    to_address=ar.email,
                    requester_name=ar.name,
                    http_client_factory=notifier_factory,
                )
            except Exception:
                logger.exception("Admin rejection email failed for %s", request_id)

    elif action == "revoke":
        try:
            ar.revoke()
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        store.update(ar)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action!r}")

    return {"id": ar.id, "status": str(ar.status)}
