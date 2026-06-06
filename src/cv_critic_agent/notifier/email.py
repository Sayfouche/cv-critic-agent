"""Transactional email via Resend.

Two templates: requester approved (session link + quota), requester rejected
(short, polite, mentions the public demo). HTML + plain text are bundled in
every send so a downgrading email client never displays an empty body.

Pure functions: api_key, from_address, to_address are arguments — no env
reads. The caller (api.py) is responsible for not logging the to_address
unmasked.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

RESEND_SEND_URL = "https://api.resend.com/emails"
DEFAULT_TIMEOUT_SECONDS = 5.0


async def _send(
    *,
    api_key: str,
    from_address: str,
    to_address: str,
    subject: str,
    text: str,
    html: str,
    http_client_factory: Callable[..., Any] | None,
    timeout: float,
) -> bool:
    """POST to Resend and return True on a 2xx response.

    Network errors and non-2xx statuses return False. The caller never has
    to inspect Resend-specific error shapes.
    """
    factory = http_client_factory or httpx.AsyncClient
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_address,
        "to": [to_address],
        "subject": subject,
        "text": text,
        "html": html,
    }
    try:
        async with factory(timeout=timeout) as client:
            response = await client.post(RESEND_SEND_URL, headers=headers, json=payload)
    except httpx.HTTPError:
        return False
    return 200 <= response.status_code < 300


async def send_requester_approved(
    *,
    api_key: str,
    from_address: str,
    to_address: str,
    requester_name: str,
    session_url: str,
    runs_quota: int,
    session_expires_in_hours: int,
    http_client_factory: Callable[..., Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bool:
    """Send the approval email with the IP-bound session link."""
    subject = "Your CV Critic Agent access request was approved"
    text = (
        f"Hi {requester_name},\n\n"
        f"Your access request has been approved.\n\n"
        f"You can run the real agent up to {runs_quota} times in the next "
        f"{session_expires_in_hours} hours by clicking this link:\n\n"
        f"{session_url}\n\n"
        f"The link is tied to the IP address of your first click — it cannot "
        f"be reused from a different device or network.\n\n"
        f"— Saifallah"
    )
    html = (
        f"<p>Hi {requester_name},</p>"
        f"<p>Your access request has been <strong>approved</strong>.</p>"
        f"<p>You can run the real agent up to <strong>{runs_quota} times</strong> "
        f"in the next <strong>{session_expires_in_hours} hours</strong> by "
        f"clicking this link:</p>"
        f'<p><a href="{session_url}">Open CV Critic Agent</a></p>'
        f'<p style="color:#666;font-size:0.9em">The link is tied to the IP '
        f"address of your first click — it cannot be reused from a different "
        f"device or network.</p>"
        f"<p>— Saifallah</p>"
    )
    return await _send(
        api_key=api_key,
        from_address=from_address,
        to_address=to_address,
        subject=subject,
        text=text,
        html=html,
        http_client_factory=http_client_factory,
        timeout=timeout,
    )


async def send_requester_rejected(
    *,
    api_key: str,
    from_address: str,
    to_address: str,
    requester_name: str,
    http_client_factory: Callable[..., Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bool:
    """Send the polite rejection email."""
    subject = "About your CV Critic Agent access request"
    text = (
        f"Hi {requester_name},\n\n"
        f"Thanks for your interest in CV Critic Agent. Unfortunately I can't "
        f"grant real-run access at this time.\n\n"
        f"You're welcome to explore the demo mode (mock runs) and the source "
        f"code on GitHub — both are public.\n\n"
        f"— Saifallah"
    )
    html = (
        f"<p>Hi {requester_name},</p>"
        f"<p>Thanks for your interest in CV Critic Agent. Unfortunately I "
        f"can't grant real-run access at this time.</p>"
        f"<p>You're welcome to explore the demo mode (mock runs) and the "
        f"source code on GitHub — both are public.</p>"
        f"<p>— Saifallah</p>"
    )
    return await _send(
        api_key=api_key,
        from_address=from_address,
        to_address=to_address,
        subject=subject,
        text=text,
        html=html,
        http_client_factory=http_client_factory,
        timeout=timeout,
    )
