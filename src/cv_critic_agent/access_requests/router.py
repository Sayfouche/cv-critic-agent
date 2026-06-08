"""FastAPI router: access-request submission + owner decision.

Endpoints
---------
POST   /api/access-requests
    Honeypot check → Turnstile verify → create AccessRequest → store →
    build HMAC decision URLs → notify owner (Telegram, fail-soft).
    Rate-limited: 3/hour per IP via slowapi.

GET    /api/access-requests/{request_id}/status
    Public. Returns {id, status} only — no PII.

GET    /api/access-requests/{request_id}/decide?token=<signed>
    Owner decision link (approve / reject). Token contains `accept` (1/0)
    to prevent URL tampering. Idempotent: already-decided requests return
    their current status without re-sending notifications.

State dependencies (all set in api.py lifespan, read via app.state):
    ar_store               AccessRequestStore | None
    hmac_secret            bytes
    turnstile_secret       str
    tg_bot_token           str
    tg_owner_chat_id       str
    resend_api_key         str
    resend_from            str
    base_url               str   API root for building decide URLs
    ui_url                 str   UI root for building session URLs
    captcha_http_factory   Callable | None   (test override)
    notifier_http_factory  Callable | None   (test override)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from cv_critic_agent.access_requests.models import (
    AccessRequest,
    AccessRequestStatus,
    InvalidTransition,
)
from cv_critic_agent.access_requests.store import AccessRequestStore
from cv_critic_agent.notifier.email import send_requester_approved, send_requester_rejected
from cv_critic_agent.notifier.telegram import send_owner_pending
from cv_critic_agent.security.crypto import sign_token, verify_token
from cv_critic_agent.security.limiter import limiter
from cv_critic_agent.security.security_middleware import verify_turnstile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/access-requests", tags=["access-requests"])

_DECIDE_TOKEN_TTL = 7 * 86_400   # 7 days
_SESSION_TOKEN_TTL = 24 * 3_600  # 24 hours


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_store(request: Request) -> AccessRequestStore:
    store: AccessRequestStore | None = getattr(request.app.state, "ar_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access request gate not configured on this server.",
        )
    return store


def _decision_page(title: str, body: str) -> HTMLResponse:
    """Minimal one-page HTML confirmation for owner decision clicks."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    body{{font-family:system-ui,sans-serif;max-width:480px;margin:80px auto;padding:0 24px;color:#222}}
    h1{{font-size:1.5rem;margin-bottom:.5rem}}
    p{{color:#555;line-height:1.6}}
    small{{color:#999}}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>{body}</p>
  <p><small>CV Critic Agent — access gate</small></p>
</body>
</html>"""
    return HTMLResponse(content=html)


async def _notify_approved(
    *,
    access_request: AccessRequest,
    hmac_secret: bytes,
    ui_url: str,
    resend_api_key: str,
    resend_from: str,
    notifier_factory: Any,
) -> None:
    """Send approval email to requester. Fail-soft."""
    if not (resend_api_key and access_request.email):
        return
    session_token = sign_token(
        {"sub": "session", "req": access_request.id},
        hmac_secret,
        _SESSION_TOKEN_TTL,
    )
    session_url = f"{ui_url}/access-granted/{session_token}"
    try:
        await send_requester_approved(
            api_key=resend_api_key,
            from_address=resend_from,
            to_address=access_request.email,
            requester_name=access_request.name,
            session_url=session_url,
            runs_quota=access_request.runs_quota,
            session_expires_in_hours=24,
            http_client_factory=notifier_factory,
        )
    except Exception:
        logger.exception("Approval email failed for request %s", access_request.id)


async def _notify_rejected(
    *,
    access_request: AccessRequest,
    resend_api_key: str,
    resend_from: str,
    notifier_factory: Any,
) -> None:
    """Send rejection email to requester. Fail-soft."""
    if not (resend_api_key and access_request.email):
        return
    try:
        await send_requester_rejected(
            api_key=resend_api_key,
            from_address=resend_from,
            to_address=access_request.email,
            requester_name=access_request.name,
            http_client_factory=notifier_factory,
        )
    except Exception:
        logger.exception("Rejection email failed for request %s", access_request.id)


# ── endpoints ────────────────────────────────────────────────────────────────

class CreateAccessRequestBody(BaseModel):
    name: str
    company: str
    email: str
    motive: str
    website: str = ""  # honeypot — must stay empty


@router.post("", status_code=200)
@limiter.limit("3/hour")
async def create_access_request(
    request: Request,
    body: CreateAccessRequestBody,
) -> dict[str, Any]:
    """Create a new access request.

    Flow: honeypot → captcha → store → build HMAC URLs → notify owner.
    Honeypot: silent 200 when `website` is filled (bots don't learn they're blocked).
    """
    # --- honeypot ---
    if body.website:
        return {"id": "bot", "status": "pending"}

    # --- captcha ---
    turnstile_secret: str = getattr(request.app.state, "turnstile_secret", "")
    captcha_factory = getattr(request.app.state, "captcha_http_factory", None)
    await verify_turnstile(request, turnstile_secret, http_client_factory=captcha_factory)

    # --- build + persist request ---
    store = _get_store(request)
    requester_ip = request.client.host if request.client else "unknown"
    ar = AccessRequest.new(
        name=body.name,
        company=body.company,
        email=body.email,
        motive=body.motive,
        requester_ip=requester_ip,
    )
    store.create(ar)

    # --- build HMAC-signed decision URLs ---
    hmac_secret: bytes = getattr(request.app.state, "hmac_secret", b"")
    base_url: str = getattr(request.app.state, "base_url", "").rstrip("/")

    approve_token = sign_token(
        {"sub": "decide", "req": ar.id, "accept": 1},
        hmac_secret,
        _DECIDE_TOKEN_TTL,
    )
    reject_token = sign_token(
        {"sub": "decide", "req": ar.id, "accept": 0},
        hmac_secret,
        _DECIDE_TOKEN_TTL,
    )
    approve_url = f"{base_url}/api/access-requests/{ar.id}/decide?token={approve_token}"
    reject_url = f"{base_url}/api/access-requests/{ar.id}/decide?token={reject_token}"

    # --- notify owner (fail-soft) ---
    tg_token: str = getattr(request.app.state, "tg_bot_token", "")
    tg_chat_id: str = getattr(request.app.state, "tg_owner_chat_id", "")
    notifier_factory = getattr(request.app.state, "notifier_http_factory", None)
    if tg_token and tg_chat_id:
        try:
            await send_owner_pending(
                bot_token=tg_token,
                owner_chat_id=tg_chat_id,
                request_id=ar.id,
                name=body.name,
                company=body.company,
                motive=body.motive,
                approve_url=approve_url,
                reject_url=reject_url,
                http_client_factory=notifier_factory,
            )
        except Exception:
            logger.exception("Telegram notify failed for request %s", ar.id)

    return {"id": ar.id, "status": str(ar.status)}


@router.get("/{request_id}/status")
async def get_status(request_id: str, request: Request) -> dict[str, Any]:
    """Return the current status of an access request (no PII)."""
    store = _get_store(request)
    ar = store.get(request_id)
    if ar is None:
        raise HTTPException(status_code=404, detail="Access request not found.")
    return {"id": ar.id, "status": str(ar.status)}


@router.get("/{request_id}/decide", response_class=HTMLResponse)
async def decide(
    request_id: str,
    token: str,
    request: Request,
) -> HTMLResponse:
    """Owner decision link — approve or reject an access request.

    The `accept` value (1 = approve, 0 = reject) is encoded inside the
    signed token to prevent URL tampering. The endpoint is idempotent: if
    the request is already decided, it returns the current status page
    without re-sending notifications.
    """
    hmac_secret: bytes = getattr(request.app.state, "hmac_secret", b"")

    # --- verify HMAC token ---
    payload = verify_token(token, hmac_secret)
    if payload is None:
        raise HTTPException(status_code=403, detail="Invalid or expired decision token.")
    if payload.get("sub") != "decide":
        raise HTTPException(status_code=403, detail="Wrong token type.")
    if payload.get("req") != request_id:
        raise HTTPException(status_code=403, detail="Token does not match request ID.")

    accept = bool(payload.get("accept"))

    # --- load request ---
    store = _get_store(request)
    ar = store.get(request_id)
    if ar is None:
        raise HTTPException(status_code=404, detail="Access request not found or expired.")

    # --- idempotent: already decided ---
    if ar.status != AccessRequestStatus.PENDING:
        return _decision_page(
            "Already decided",
            f"This request is already <strong>{ar.status}</strong>. No action taken.",
        )

    # --- apply decision ---
    notifier_factory = getattr(request.app.state, "notifier_http_factory", None)
    resend_key: str = getattr(request.app.state, "resend_api_key", "")
    resend_from: str = getattr(request.app.state, "resend_from", "")
    ui_url: str = getattr(request.app.state, "ui_url", "").rstrip("/")

    if accept:
        try:
            ar.approve()
        except InvalidTransition:
            return _decision_page("Already decided", "Cannot approve from current state.")
        # Commit BEFORE sending email (email is fail-soft; state must be durable first).
        store.update(ar)
        await _notify_approved(
            access_request=ar,
            hmac_secret=hmac_secret,
            ui_url=ui_url,
            resend_api_key=resend_key,
            resend_from=resend_from,
            notifier_factory=notifier_factory,
        )
        return _decision_page(
            "Request approved ✅",
            "The requester will receive an email with their session link.",
        )
    else:
        try:
            ar.reject()
        except InvalidTransition:
            return _decision_page("Already decided", "Cannot reject from current state.")
        store.update(ar)
        await _notify_rejected(
            access_request=ar,
            resend_api_key=resend_key,
            resend_from=resend_from,
            notifier_factory=notifier_factory,
        )
        return _decision_page(
            "Request rejected ❌",
            "The requester has been notified.",
        )
