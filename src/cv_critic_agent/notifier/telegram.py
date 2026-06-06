"""Telegram bot notifications: owner pending + budget alert.

One direction (we send, we don't poll). Sent message_ids are not stored —
Telegram keeps them itself, and we don't need to edit later in V1.

Pure functions: bot_token, owner_chat_id, http_client_factory are arguments,
never module globals. Failures fail-soft: return False, log nothing
sensitive. The caller decides whether to fall back to email or alert.

Approve / Reject URLs are passed in already-signed by the caller. This module
does not know about HMAC or the access-request lifecycle — it just delivers
two URLs and a status text.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

TELEGRAM_API_TEMPLATE = "https://api.telegram.org/bot{token}/{method}"
DEFAULT_TIMEOUT_SECONDS = 5.0


def _api_url(bot_token: str, method: str) -> str:
    return TELEGRAM_API_TEMPLATE.format(token=bot_token, method=method)


async def _post(
    url: str,
    payload: dict,
    *,
    http_client_factory: Callable[..., Any] | None,
    timeout: float,
) -> bool:
    """POST to Telegram and return True only if Telegram replied ok=True.

    Any of: network error, non-200 status, malformed JSON, or
    ``payload["ok"] is False`` → returns False. The caller never has to
    inspect Telegram-specific error shapes.
    """
    factory = http_client_factory or httpx.AsyncClient
    try:
        async with factory(timeout=timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError:
        return False
    if response.status_code != 200:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    return bool(body.get("ok"))


async def send_owner_pending(
    *,
    bot_token: str,
    owner_chat_id: int | str,
    request_id: str,
    name: str,
    company: str,
    motive: str,
    approve_url: str,
    reject_url: str,
    http_client_factory: Callable[..., Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bool:
    """Notify the owner of a new access request, with inline Approve/Reject buttons.

    The two URLs must already carry their HMAC signatures: this module does
    not know how to sign them. Returns True iff Telegram accepted the send.
    """
    text = (
        "🔔 *New access request*\n\n"
        f"*From:* {name} — {company}\n"
        f"*Motive:* {motive}\n\n"
        f"`{request_id}`"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "url": approve_url},
                {"text": "❌ Reject", "url": reject_url},
            ]
        ]
    }
    body = {
        "chat_id": owner_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    }
    return await _post(
        _api_url(bot_token, "sendMessage"),
        body,
        http_client_factory=http_client_factory,
        timeout=timeout,
    )


async def send_budget_alert(
    *,
    bot_token: str,
    owner_chat_id: int | str,
    percentage: int,
    tokens_used: int,
    daily_cap: int,
    http_client_factory: Callable[..., Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bool:
    """Notify the owner when the daily Mistral budget threshold is crossed.

    Called from budget_tracker.py once for 80% and once for 100%. At 100%
    real runs degrade silently to mock, so the alert is the only signal.
    """
    severity = "⚠️" if percentage < 100 else "🚨"
    title = "Budget warning" if percentage < 100 else "Budget cap hit"
    text = (
        f"{severity} *{title} ({percentage}%)*\n\n"
        f"Tokens used: {tokens_used:,} / {daily_cap:,}"
    )
    if percentage >= 100:
        text += "\n\nReal runs degrade to mock until midnight UTC."
    body = {
        "chat_id": owner_chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    return await _post(
        _api_url(bot_token, "sendMessage"),
        body,
        http_client_factory=http_client_factory,
        timeout=timeout,
    )


def is_owner_callback(
    callback_from_id: int | str | None,
    owner_chat_id: int | str,
) -> bool:
    """True iff a Telegram callback_query.from.id matches the configured owner.

    Used by /api/telegram/webhook to silently drop spoofed callbacks. We
    compare by string because the Telegram payload sends a JSON number that
    can deserialise as int or float depending on intermediates.
    """
    if callback_from_id is None or owner_chat_id == "":
        return False
    return str(callback_from_id) == str(owner_chat_id)
