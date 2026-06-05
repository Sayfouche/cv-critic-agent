"""Logging filter that masks email addresses in every log record.

Installed once via `install_email_masking()`. After that, any log line that
contains an email — whether the caller built the string itself or passed the
email as a `%s` argument — appears as `a****@example.com`. Local-part stripped,
domain kept (incident triage still benefits from "we leaked an @gmail user").

This guards against the most common PII leak vector in a Python service:
`logger.info("user %s logged in", request.email)` slipping past a code review.
"""
from __future__ import annotations

import logging
import re
from typing import Any

# Simplified RFC 5322 — good enough for masking, not for validation.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _mask_one(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[0]}****@{domain}" if local else email


def _mask_text(text: str) -> str:
    return _EMAIL_RE.sub(lambda m: _mask_one(m.group(0)), text)


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        return _mask_text(value)
    if isinstance(value, tuple):
        return tuple(_mask_value(item) for item in value)
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _mask_value(v) for k, v in value.items()}
    return value


class EmailMaskingFilter(logging.Filter):
    """Mutates each record so emails are masked when the line is formatted."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _mask_text(record.msg)
        if record.args:
            record.args = _mask_value(record.args)
        return True


def install_email_masking() -> None:
    """Attach the masking filter to root logger and every existing handler.

    Idempotent — repeat calls are no-ops. Safe to call from app startup and
    from tests. Future-created loggers inherit via propagation; future-created
    handlers should call this helper again (cheap, idempotent) after setup.
    """
    filt = EmailMaskingFilter()
    root = logging.getLogger()
    if not any(isinstance(f, EmailMaskingFilter) for f in root.filters):
        root.addFilter(filt)
    for handler in root.handlers:
        if not any(isinstance(f, EmailMaskingFilter) for f in handler.filters):
            handler.addFilter(EmailMaskingFilter())
