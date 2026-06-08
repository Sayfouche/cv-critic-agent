"""FastAPI router: POST /api/telegram/webhook.

Handles incoming Telegram Update objects. Two interaction patterns:

1. callback_query — inline keyboard buttons with callback_data.
   Expected format: "approve:{request_id}" | "reject:{request_id}"
   Owner identity verified via TELEGRAM_OWNER_CHAT_ID comparison.

2. message with text "/approve {request_id}" | "/reject {request_id}"
   Text commands as a fallback when inline buttons are not available.

Security:
- Always validates that the sender is the configured owner (chat_id match).
- Non-owner callbacks are dropped silently with HTTP 200 (Telegram must
  always get 200, otherwise it retries indefinitely).
- Duplicate decisions are idempotent (already-decided requests are silently
  acknowledged).

State dependencies (set by api.py lifespan, read via app.state):
    tg_owner_chat_id       str
    tg_bot_token           str
    ar_store               AccessRequestStore | None
    hmac_secret            bytes
    resend_api_key         str
    resend_from            str
    ui_url                 str
    notifier_http_factory  Callable | None
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from cv_critic_agent.access_requests.models import AccessRequestStatus, InvalidTransition
from cv_critic_agent.access_requests.store import AccessRequestStore
from cv_critic_agent.notifier.telegram import is_owner_callback
from cv_critic_agent.security.crypto import sign_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram"])

_SESSION_TOKEN_TTL = 24 * 3_600


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_command(text: str) -> tuple[str, str] | None:
    """Parse '/approve req-id' or '/reject req-id' → ('approve'|'reject', req_id).

    Returns None for any other input.
    """
    text = text.strip()
    parts = text.split(None, 1)
    if len(parts) != 2:
        return None
    cmd, arg = parts
    cmd = cmd.lstrip("/").lower()
    if cmd not in ("approve", "reject"):
        return None
    return cmd, arg.strip()


async def _process_decision(
    *,
    request_id: str,
    accept: bool,
    app_state: Any,
) -> str:
    """Apply decision to an access request and send notifications.

    Returns a short status string for logging. Fail-soft: never raises.
    """
    store: AccessRequestStore | None = getattr(app_state, "ar_store", None)
    if store is None:
        return "store_not_configured"

    ar = store.get(request_id)
    if ar is None:
        return "not_found"

    if ar.status != AccessRequestStatus.PENDING:
        return f"already_{ar.status}"

    hmac_secret: bytes = getattr(app_state, "hmac_secret", b"")
    resend_key: str = getattr(app_state, "resend_api_key", "")
    resend_from: str = getattr(app_state, "resend_from", "")
    ui_url: str = getattr(app_state, "ui_url", "").rstrip("/")
    notifier_factory = getattr(app_state, "notifier_http_factory", None)

    if accept:
        try:
            ar.approve()
        except InvalidTransition:
            return "invalid_transition"
        store.update(ar)

        # Send approval email (fail-soft)
        if resend_key and ar.email:
            from cv_critic_agent.notifier.email import send_requester_approved

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
                logger.exception("Approval email failed (webhook) for %s", request_id)
        return "approved"
    else:
        try:
            ar.reject()
        except InvalidTransition:
            return "invalid_transition"
        store.update(ar)

        if resend_key and ar.email:
            from cv_critic_agent.notifier.email import send_requester_rejected

            try:
                await send_requester_rejected(
                    api_key=resend_key,
                    from_address=resend_from,
                    to_address=ar.email,
                    requester_name=ar.name,
                    http_client_factory=notifier_factory,
                )
            except Exception:
                logger.exception("Rejection email failed (webhook) for %s", request_id)
        return "rejected"


# ── endpoint ─────────────────────────────────────────────────────────────────

@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request) -> dict[str, bool]:
    """Receive Telegram Update objects from the configured webhook.

    Always returns {"ok": True} with HTTP 200 — Telegram requires this to
    stop retrying. Errors are logged but never surfaced to Telegram.
    """
    owner_chat_id: str = getattr(request.app.state, "tg_owner_chat_id", "")

    try:
        body: dict = await request.json()
    except Exception:
        return {"ok": True}

    # ── callback_query (inline keyboard) ─────────────────────────────────────
    callback_query = body.get("callback_query")
    if callback_query:
        from_id = (callback_query.get("from") or {}).get("id")
        if not is_owner_callback(from_id, owner_chat_id):
            logger.info("Telegram webhook: non-owner callback_query from %s — dropped", from_id)
            return {"ok": True}

        data: str = callback_query.get("data", "")
        parts = data.split(":", 1)
        if len(parts) == 2:
            action, req_id = parts
            accept = action.lower() == "approve"
            result = await _process_decision(
                request_id=req_id,
                accept=accept,
                app_state=request.app.state,
            )
            logger.info("Telegram webhook: callback_query %s %s → %s", action, req_id, result)
        return {"ok": True}

    # ── message (text command) ────────────────────────────────────────────────
    message = body.get("message")
    if message:
        from_id = (message.get("from") or {}).get("id")
        if not is_owner_callback(from_id, owner_chat_id):
            return {"ok": True}

        text: str = message.get("text", "")
        parsed = _parse_command(text)
        if parsed:
            action, req_id = parsed
            accept = action == "approve"
            result = await _process_decision(
                request_id=req_id,
                accept=accept,
                app_state=request.app.state,
            )
            logger.info("Telegram webhook: message /%s %s → %s", action, req_id, result)

    return {"ok": True}
