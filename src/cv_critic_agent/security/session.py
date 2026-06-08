"""Session-token verification for real-mode ``POST /api/runs``.

A *session token* is the HMAC-signed value emailed to a requester whose
access request has been approved (see ``access_requests/router.py`` and
``admin/router.py``). The token's payload is ``{"sub": "session", "req":
"<access_request_id>", "exp": <unix>}``.

``verify_session`` is a **pure read**: signature → record lookup → state
checks → IP-binding peek → quota peek. It never mutates the store. The
caller atomically consumes a run via ``AccessRequestStore.atomic_consume_run``
after this function returns.

Failure modes raise typed exceptions so the HTTP endpoint can pick the
right status code (and never leak attacker-controlled state in messages).
"""
from __future__ import annotations

from cv_critic_agent.access_requests.models import (
    AccessRequest,
    AccessRequestStatus,
)
from cv_critic_agent.access_requests.store import AccessRequestStore
from cv_critic_agent.security.crypto import verify_token


class InvalidSessionToken(Exception):
    """Signature/expiry/format failure — token is untrusted."""


class SessionNotApproved(Exception):
    """Token decoded but the underlying request is not in APPROVED state."""


class SessionIpMismatch(Exception):
    """Session was first used from a different IP than the current request."""


class SessionQuotaExceeded(Exception):
    """All ``runs_quota`` runs have already been consumed."""


def verify_session(
    token: str,
    request_ip: str,
    hmac_secret: bytes,
    ar_store: AccessRequestStore,
) -> AccessRequest:
    """Validate a session token and return the eligible AccessRequest.

    Does not mutate the store. The caller must invoke
    ``ar_store.atomic_consume_run(ar.id, request_ip)`` to actually consume
    a slot.

    Raises:
        InvalidSessionToken: token missing, malformed, signature mismatch,
            past ``exp``, wrong ``sub``, or missing ``req`` field. Also
            raised when ``request_ip`` is empty.
        SessionNotApproved: the access request does not exist, or its
            status is not ``APPROVED``.
        SessionIpMismatch: the request has already been used from a
            different IP than ``request_ip``.
        SessionQuotaExceeded: the request has already used its
            ``runs_quota`` (status would normally be ``CONSUMED`` but we
            check the counter directly to cover edge cases).
    """
    if not request_ip:
        raise InvalidSessionToken("request_ip required")

    payload = verify_token(token, hmac_secret)
    if payload is None or payload.get("sub") != "session":
        raise InvalidSessionToken("token invalid")
    req_id = payload.get("req")
    if not isinstance(req_id, str) or not req_id:
        raise InvalidSessionToken("missing req in token")

    ar = ar_store.get(req_id)
    if ar is None or ar.status != AccessRequestStatus.APPROVED:
        raise SessionNotApproved("request not approved")

    if ar.session_ip_binding is not None and ar.session_ip_binding != request_ip:
        raise SessionIpMismatch("session bound to a different IP")

    if ar.runs_used >= ar.runs_quota:
        raise SessionQuotaExceeded("runs_quota exhausted")

    return ar
