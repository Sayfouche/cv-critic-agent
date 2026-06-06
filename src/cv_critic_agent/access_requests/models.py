"""Data model for human-in-the-loop access requests.

In-memory representation. Encryption at rest is the store layer's job, not
the dataclass's — keep this module about state-machine invariants only.

State machine:

    PENDING ──approve──► APPROVED ──consume*──► CONSUMED
        │                   │
        │                   └──revoke──► REVOKED
        │
        └──reject──► REJECTED

    any ──ttl sweep──► EXPIRED

Transitions raise InvalidTransition when called from the wrong state, so the
caller never silently writes a forbidden status. Quota and IP-binding
violations have their own typed exceptions for the same reason.
"""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass

DEFAULT_RUNS_QUOTA = 3
DEFAULT_SESSION_TTL_SECONDS = 24 * 3600
PENDING_TTL_SECONDS = 7 * 86400
DECIDED_TTL_SECONDS = 90 * 86400


class AccessRequestStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InvalidTransition(Exception):
    """State-machine violation."""


class QuotaExceeded(Exception):
    """Cannot consume another run: runs_quota reached."""


class IpBindingMismatch(Exception):
    """Session used from a different IP than the first call."""


@dataclass
class AccessRequest:
    id: str
    name: str
    company: str
    email: str
    motive: str
    requester_ip: str
    created_at: float
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    decided_at: float | None = None
    session_expires_at: float | None = None
    session_ip_binding: str | None = None
    runs_used: int = 0
    runs_quota: int = DEFAULT_RUNS_QUOTA

    @classmethod
    def new(
        cls,
        *,
        name: str,
        company: str,
        email: str,
        motive: str,
        requester_ip: str,
    ) -> AccessRequest:
        return cls(
            id=uuid.uuid4().hex,
            name=name,
            company=company,
            email=email,
            motive=motive,
            requester_ip=requester_ip,
            created_at=time.time(),
        )

    # ── State transitions ───────────────────────────────────────────────────
    def approve(
        self, session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    ) -> None:
        if self.status != AccessRequestStatus.PENDING:
            raise InvalidTransition(f"cannot approve from {self.status.value}")
        now = time.time()
        self.status = AccessRequestStatus.APPROVED
        self.decided_at = now
        self.session_expires_at = now + session_ttl_seconds

    def reject(self) -> None:
        if self.status != AccessRequestStatus.PENDING:
            raise InvalidTransition(f"cannot reject from {self.status.value}")
        self.status = AccessRequestStatus.REJECTED
        self.decided_at = time.time()

    def consume_one_run(self) -> None:
        if self.status != AccessRequestStatus.APPROVED:
            raise InvalidTransition(
                f"cannot consume run from {self.status.value}"
            )
        if self.runs_used >= self.runs_quota:
            raise QuotaExceeded("runs_quota exhausted")
        self.runs_used += 1
        if self.runs_used >= self.runs_quota:
            self.status = AccessRequestStatus.CONSUMED

    def bind_ip(self, ip: str) -> None:
        """First call records; subsequent calls must match the recorded IP."""
        if not ip:
            raise ValueError("ip must be non-empty")
        if self.session_ip_binding is None:
            self.session_ip_binding = ip
            return
        if self.session_ip_binding != ip:
            raise IpBindingMismatch("session bound to a different IP")

    def revoke(self) -> None:
        """Owner pulls an APPROVED session back. Idempotent for REVOKED."""
        if self.status == AccessRequestStatus.REVOKED:
            return
        if self.status != AccessRequestStatus.APPROVED:
            raise InvalidTransition(f"cannot revoke from {self.status.value}")
        self.status = AccessRequestStatus.REVOKED

    def mark_expired(self) -> None:
        """Cron sweep: idempotent move to EXPIRED for PENDING and APPROVED."""
        if self.status not in (
            AccessRequestStatus.PENDING,
            AccessRequestStatus.APPROVED,
        ):
            return
        self.status = AccessRequestStatus.EXPIRED

    # ── Predicates ──────────────────────────────────────────────────────────
    def is_session_valid(self, now: float | None = None) -> bool:
        if self.status != AccessRequestStatus.APPROVED:
            return False
        if self.runs_used >= self.runs_quota:
            return False
        if self.session_expires_at is None:
            return False
        ts = now if now is not None else time.time()
        return self.session_expires_at > ts

    def is_pending_expired(self, now: float | None = None) -> bool:
        if self.status != AccessRequestStatus.PENDING:
            return False
        ts = now if now is not None else time.time()
        return ts - self.created_at > PENDING_TTL_SECONDS

    def is_decided_purgeable(self, now: float | None = None) -> bool:
        if self.status not in (
            AccessRequestStatus.REJECTED,
            AccessRequestStatus.CONSUMED,
            AccessRequestStatus.EXPIRED,
            AccessRequestStatus.REVOKED,
        ):
            return False
        ref = self.decided_at if self.decided_at is not None else self.created_at
        ts = now if now is not None else time.time()
        return ts - ref > DECIDED_TTL_SECONDS
