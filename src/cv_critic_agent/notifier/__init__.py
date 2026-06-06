"""Notifier layer — Telegram bot + Resend transactional email.

Pure-function modules: every dependency (token, key, addresses,
http_client_factory) is passed explicitly. No env reads, no module-level
clients. Failures are fail-soft (return False), never raise — the caller
decides whether to retry, alert, or both.
"""
