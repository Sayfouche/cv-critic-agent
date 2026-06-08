"""Persistent storage for AccessRequest objects.

One JSON file per request: ``<base_dir>/<request_id>.json``.
All PII fields (name, company, email, motive) are encrypted with Fernet at
write time and decrypted at read time. The rest of the payload is stored
plaintext so it can be indexed without decryption.

File-level locking
------------------
Every read and write acquires an exclusive ``fcntl.flock`` on the open
file descriptor before touching the bytes. This is advisory but sufficient
for the single-process, multi-thread scenario of a Render web service.

Lazy cleanup
------------
``get()`` calls ``is_pending_expired()`` and ``is_decided_purgeable()`` on
the just-loaded record. If either is true the file is deleted and ``None``
is returned, exactly as if the record had never existed. This avoids the
need for a background thread to stay alive; the cron script
(``scripts/cleanup_access_requests.py``, tâche #19) still handles bulk
sweeps at off-hours.
"""
from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

from cv_critic_agent.access_requests.models import (
    AccessRequest,
    AccessRequestStatus,
    IpBindingMismatch,
    InvalidTransition,
    QuotaExceeded,
    SessionExpired,
)
from cv_critic_agent.security.pii import decrypt_pii, encrypt_pii

# Fields whose values are encrypted at rest.
_PII_FIELDS: tuple[str, ...] = ("name", "company", "email", "motive")


def _to_dict(req: AccessRequest, fernet_key: bytes) -> dict:
    """Serialise an AccessRequest to a plain-JSON-compatible dict.

    PII fields are replaced by their Fernet ciphertext.  All other fields
    are kept as-is (strings, floats, ints, None).  The status StrEnum
    serialises as its string value automatically via ``str()``.
    """
    raw: dict = {
        "id": req.id,
        "status": str(req.status),
        "requester_ip": req.requester_ip,
        "created_at": req.created_at,
        "decided_at": req.decided_at,
        "session_expires_at": req.session_expires_at,
        "session_ip_binding": req.session_ip_binding,
        "runs_used": req.runs_used,
        "runs_quota": req.runs_quota,
    }
    for field in _PII_FIELDS:
        raw[field] = encrypt_pii(getattr(req, field), fernet_key)
    return raw


def _from_dict(data: dict, fernet_key: bytes) -> AccessRequest:
    """Deserialise a stored dict back to an AccessRequest.

    PII fields are decrypted.  An unrecognised status value is mapped to
    EXPIRED as a safe fallback (corrupted file).
    """
    pii: dict[str, str] = {}
    for field in _PII_FIELDS:
        raw_value = data.get(field, "")
        decrypted = decrypt_pii(raw_value, fernet_key) if raw_value else None
        pii[field] = decrypted or ""

    try:
        status = AccessRequestStatus(data["status"])
    except (KeyError, ValueError):
        status = AccessRequestStatus.EXPIRED

    return AccessRequest(
        id=data["id"],
        name=pii["name"],
        company=pii["company"],
        email=pii["email"],
        motive=pii["motive"],
        requester_ip=data.get("requester_ip", ""),
        created_at=float(data.get("created_at", 0.0)),
        status=status,
        decided_at=data.get("decided_at"),
        session_expires_at=data.get("session_expires_at"),
        session_ip_binding=data.get("session_ip_binding"),
        runs_used=int(data.get("runs_used", 0)),
        runs_quota=int(data.get("runs_quota", 3)),
    )


class AccessRequestStore:
    """CRUD store backed by one-JSON-file-per-request on the local filesystem.

    Parameters
    ----------
    base_dir:
        Directory where ``<request_id>.json`` files are written.  Created
        automatically on first use.
    fernet_key:
        Raw Fernet key bytes (32 url-safe base64-encoded bytes, i.e. the
        value of ``Fernet.generate_key()``).  Passed straight to
        ``encrypt_pii`` / ``decrypt_pii``.
    """

    def __init__(self, base_dir: Path, fernet_key: bytes) -> None:
        self._base_dir = Path(base_dir)
        self._fernet_key = fernet_key
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _path(self, request_id: str) -> Path:
        return self._base_dir / f"{request_id}.json"

    # ── Public API ───────────────────────────────────────────────────────────

    def create(self, request: AccessRequest) -> None:
        """Write a new request to disk.  Raises ``FileExistsError`` if the
        file already exists (duplicate IDs must never silently overwrite)."""
        dest = self._path(request.id)
        if dest.exists():
            raise FileExistsError(f"access request {request.id!r} already exists")
        payload = json.dumps(_to_dict(request, self._fernet_key), ensure_ascii=False)
        # Create with exclusive flag so two concurrent creates on the same ID
        # still fail at the OS level (advisory lock alone won't protect open-create).
        with dest.open("x", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.write(payload)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def get(self, request_id: str) -> AccessRequest | None:
        """Return the request or ``None`` if it doesn't exist or has expired.

        Lazy TTL: if the loaded record is past its pending or decided TTL it
        is purged from disk and ``None`` is returned.
        """
        path = self._path(request_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                fcntl.flock(fh, fcntl.LOCK_SH)
                try:
                    data = json.load(fh)
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        except (OSError, json.JSONDecodeError):
            return None

        req = _from_dict(data, self._fernet_key)

        # Lazy cleanup: silently drop expired / purgeable records.
        if req.is_pending_expired() or req.is_decided_purgeable():
            path.unlink(missing_ok=True)
            return None

        return req

    def atomic_consume_run(self, request_id: str, ip: str) -> AccessRequest:
        """Consume one run under an exclusive file lock.

        Critical section: read → validate → mutate → write, all while holding
        ``LOCK_EX`` on the request file. Two concurrent calls on the same
        request can never both increment ``runs_used`` past the quota.

        Raises:
            FileNotFoundError: request_id unknown.
            InvalidTransition: status is not APPROVED (already consumed,
                rejected, revoked, expired by TTL sweep, …).
            SessionExpired: status APPROVED but ``session_expires_at`` past;
                the record is mutated to EXPIRED and persisted before raising.
            IpBindingMismatch: ``session_ip_binding`` is set to a different IP.
            QuotaExceeded: ``runs_used >= runs_quota``.
        """
        if not ip:
            raise ValueError("ip must be non-empty")
        path = self._path(request_id)
        if not path.exists():
            raise FileNotFoundError(f"access request {request_id!r} not found")
        with path.open("r+", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                data = json.load(fh)
                req = _from_dict(data, self._fernet_key)
                if req.status != AccessRequestStatus.APPROVED:
                    raise InvalidTransition(
                        f"cannot consume run from {req.status.value}"
                    )
                now = time.time()
                if (
                    req.session_expires_at is not None
                    and req.session_expires_at <= now
                ):
                    req.mark_expired()
                    fh.seek(0)
                    fh.write(
                        json.dumps(_to_dict(req, self._fernet_key), ensure_ascii=False)
                    )
                    fh.truncate()
                    raise SessionExpired("session past session_expires_at")
                req.bind_ip(ip)  # raises IpBindingMismatch
                req.consume_one_run()  # raises QuotaExceeded
                fh.seek(0)
                fh.write(
                    json.dumps(_to_dict(req, self._fernet_key), ensure_ascii=False)
                )
                fh.truncate()
                return req
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def update(self, request: AccessRequest) -> None:
        """Overwrite an existing record.  Raises ``FileNotFoundError`` if the
        file doesn't exist (use ``create`` for new records)."""
        path = self._path(request.id)
        if not path.exists():
            raise FileNotFoundError(f"access request {request.id!r} not found")
        payload = json.dumps(_to_dict(request, self._fernet_key), ensure_ascii=False)
        with path.open("r+", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                fh.write(payload)
                fh.truncate()
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def delete(self, request_id: str) -> bool:
        """Delete a request file.  Returns ``True`` if the file existed and
        was deleted, ``False`` if it was already absent."""
        path = self._path(request_id)
        if not path.exists():
            return False
        path.unlink(missing_ok=True)
        return True

    def list_by_status(self, status: AccessRequestStatus) -> list[AccessRequest]:
        """Return all non-expired requests matching *status*.

        Expired / purgeable records encountered during the scan are silently
        purged (same lazy-cleanup rule as ``get``).
        """
        results: list[AccessRequest] = []
        for json_path in sorted(self._base_dir.glob("*.json")):
            request_id = json_path.stem
            req = self.get(request_id)  # get() handles lazy cleanup
            if req is not None and req.status == status:
                results.append(req)
        return results

    def cleanup_expired(self) -> int:
        """Purge all files whose records are past pending or decided TTL.

        Returns the count of files deleted.  This is safe to call from a
        cron job alongside concurrent web workers because each deletion is
        atomic at the filesystem level.
        """
        count = 0
        for json_path in list(self._base_dir.glob("*.json")):
            request_id = json_path.stem
            result = self.get(request_id)
            # ``get()`` already deleted the file if it was expired, and
            # returned None.  We can count the files that disappeared.
            if result is None and not json_path.exists():
                count += 1
        return count
