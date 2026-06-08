"""Tests for AccessRequestStore — JSON/fcntl persistence layer.

Coverage:
    - create/get round-trip with PII Fernet encryption
    - duplicate create raises FileExistsError
    - get returns None for unknown ID
    - get purges pending-expired records lazily (returns None + deletes file)
    - get purges decided-purgeable records lazily (returns None + deletes file)
    - update overwrites an existing record
    - update raises FileNotFoundError for a missing record
    - delete returns True when file exists, False when absent
    - list_by_status filters by status, skips other statuses
    - cleanup_expired deletes all stale files and returns the count
    - PII is not stored in plaintext on disk
    - concurrency: N threads each create a distinct record, all remain readable
"""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from cryptography.fernet import Fernet

from cv_critic_agent.access_requests.models import (
    DECIDED_TTL_SECONDS,
    PENDING_TTL_SECONDS,
    AccessRequest,
    AccessRequestStatus,
    InvalidTransition,
    IpBindingMismatch,
    QuotaExceeded,
    SessionExpired,
)
from cv_critic_agent.access_requests.store import AccessRequestStore

KEY: bytes = Fernet.generate_key()
OTHER_KEY: bytes = Fernet.generate_key()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make() -> AccessRequest:
    return AccessRequest.new(
        name="Alice",
        company="ACME Corp",
        email="alice@example.com",
        motive="testing the access gate",
        requester_ip="1.2.3.4",
    )


def _store(base_dir: Path, key: bytes = KEY) -> AccessRequestStore:
    return AccessRequestStore(base_dir=base_dir, fernet_key=key)


class TempDirMixin(unittest.TestCase):
    """Provides self.base_dir, a fresh temp directory per test."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="cv-critic-store-")
        self.base_dir = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


# ── Round-trip ────────────────────────────────────────────────────────────────


class RoundTripTests(TempDirMixin):
    def test_create_get_returns_equivalent_record(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)

        got = store.get(req.id)
        self.assertIsNotNone(got)
        assert got is not None  # narrow type

        self.assertEqual(got.id, req.id)
        self.assertEqual(got.name, req.name)
        self.assertEqual(got.company, req.company)
        self.assertEqual(got.email, req.email)
        self.assertEqual(got.motive, req.motive)
        self.assertEqual(got.requester_ip, req.requester_ip)
        self.assertEqual(got.status, AccessRequestStatus.PENDING)

    def test_create_get_preserves_unicode_pii(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.name = "Saïfallah"
        req.company = "BNP Paribas Asset Management"
        req.email = "saïf@élysée.fr"
        req.motive = "Je veux tester votre agent IA 🤖"
        store.create(req)

        got = store.get(req.id)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.name, "Saïfallah")
        self.assertEqual(got.motive, "Je veux tester votre agent IA 🤖")

    def test_create_get_preserves_all_numeric_fields(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.approve()
        req.consume_one_run()
        store.create(req)

        got = store.get(req.id)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.runs_used, 1)
        self.assertEqual(got.runs_quota, req.runs_quota)
        self.assertAlmostEqual(got.decided_at or 0, req.decided_at or 0, delta=2.0)  # type: ignore[arg-type]

    def test_get_unknown_id_returns_none(self) -> None:
        store = _store(self.base_dir)
        self.assertIsNone(store.get("nonexistent"))


# ── Duplicate / missing guards ────────────────────────────────────────────────


class CreateGuardTests(TempDirMixin):
    def test_duplicate_create_raises_file_exists_error(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)
        with self.assertRaises(FileExistsError):
            store.create(req)  # same id, same object — must fail

    def test_update_missing_record_raises_file_not_found(self) -> None:
        store = _store(self.base_dir)
        with self.assertRaises(FileNotFoundError):
            store.update(_make())


# ── Lazy TTL ──────────────────────────────────────────────────────────────────


class LazyTTLTests(TempDirMixin):
    def test_get_purges_pending_expired_and_returns_none(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        # Back-date creation so pending TTL is exceeded
        req.created_at = time.time() - PENDING_TTL_SECONDS - 1
        store.create(req)

        json_path = self.base_dir / f"{req.id}.json"
        self.assertTrue(json_path.exists())

        result = store.get(req.id)
        self.assertIsNone(result)
        self.assertFalse(json_path.exists(), "file must be purged on lazy TTL hit")

    def test_get_purges_decided_purgeable_and_returns_none(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.reject()
        # Back-date decision so decided TTL is exceeded
        req.decided_at = time.time() - DECIDED_TTL_SECONDS - 1
        store.create(req)

        json_path = self.base_dir / f"{req.id}.json"
        self.assertTrue(json_path.exists())

        result = store.get(req.id)
        self.assertIsNone(result)
        self.assertFalse(json_path.exists(), "file must be purged on lazy TTL hit")

    def test_get_returns_record_before_pending_ttl(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)
        self.assertIsNotNone(store.get(req.id))

    def test_get_returns_record_before_decided_ttl(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.reject()
        store.create(req)
        self.assertIsNotNone(store.get(req.id))


# ── Update ────────────────────────────────────────────────────────────────────


class UpdateTests(TempDirMixin):
    def test_update_overwrites_status(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)

        req.approve()
        store.update(req)

        got = store.get(req.id)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.status, AccessRequestStatus.APPROVED)

    def test_update_overwrites_runs_used(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.approve()
        store.create(req)

        req.consume_one_run()
        store.update(req)

        got = store.get(req.id)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.runs_used, 1)

    def test_update_overwrites_ip_binding(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.approve()
        store.create(req)

        req.bind_ip("9.8.7.6")
        store.update(req)

        got = store.get(req.id)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.session_ip_binding, "9.8.7.6")


# ── Delete ────────────────────────────────────────────────────────────────────


class DeleteTests(TempDirMixin):
    def test_delete_existing_returns_true(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)
        self.assertTrue(store.delete(req.id))

    def test_delete_missing_returns_false(self) -> None:
        store = _store(self.base_dir)
        self.assertFalse(store.delete("does-not-exist"))

    def test_deleted_record_is_not_readable(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)
        store.delete(req.id)
        self.assertIsNone(store.get(req.id))


# ── list_by_status ────────────────────────────────────────────────────────────


class ListByStatusTests(TempDirMixin):
    def _populate(self, store: AccessRequestStore) -> tuple[AccessRequest, AccessRequest, AccessRequest]:
        """Create three records: one pending, one approved, one rejected."""
        pending = _make()
        store.create(pending)

        approved = _make()
        approved.approve()
        store.create(approved)

        rejected = _make()
        rejected.reject()
        store.create(rejected)

        return pending, approved, rejected

    def test_list_pending_returns_only_pending_records(self) -> None:
        store = _store(self.base_dir)
        pending, _, _ = self._populate(store)
        result = store.list_by_status(AccessRequestStatus.PENDING)
        ids = {r.id for r in result}
        self.assertIn(pending.id, ids)
        self.assertEqual(len(result), 1)

    def test_list_approved_returns_only_approved_records(self) -> None:
        store = _store(self.base_dir)
        _, approved, _ = self._populate(store)
        result = store.list_by_status(AccessRequestStatus.APPROVED)
        ids = {r.id for r in result}
        self.assertIn(approved.id, ids)
        self.assertEqual(len(result), 1)

    def test_list_rejected_returns_only_rejected_records(self) -> None:
        store = _store(self.base_dir)
        _, _, rejected = self._populate(store)
        result = store.list_by_status(AccessRequestStatus.REJECTED)
        ids = {r.id for r in result}
        self.assertIn(rejected.id, ids)
        self.assertEqual(len(result), 1)

    def test_list_for_absent_status_returns_empty(self) -> None:
        store = _store(self.base_dir)
        self._populate(store)
        result = store.list_by_status(AccessRequestStatus.CONSUMED)
        self.assertEqual(result, [])

    def test_list_skips_lazily_expired_records(self) -> None:
        store = _store(self.base_dir)
        # Create an expired pending record
        stale = _make()
        stale.created_at = time.time() - PENDING_TTL_SECONDS - 1
        store.create(stale)

        result = store.list_by_status(AccessRequestStatus.PENDING)
        ids = {r.id for r in result}
        self.assertNotIn(stale.id, ids)


# ── cleanup_expired ───────────────────────────────────────────────────────────


class CleanupExpiredTests(TempDirMixin):
    def test_cleanup_returns_count_of_deleted_files(self) -> None:
        store = _store(self.base_dir)

        # Two stale pending records
        for _ in range(2):
            stale = _make()
            stale.created_at = time.time() - PENDING_TTL_SECONDS - 1
            store.create(stale)

        # One live record
        live = _make()
        store.create(live)

        count = store.cleanup_expired()
        self.assertEqual(count, 2)

    def test_cleanup_leaves_live_records_intact(self) -> None:
        store = _store(self.base_dir)
        live = _make()
        store.create(live)

        store.cleanup_expired()
        self.assertIsNotNone(store.get(live.id))

    def test_cleanup_idempotent_on_empty_directory(self) -> None:
        store = _store(self.base_dir)
        self.assertEqual(store.cleanup_expired(), 0)


# ── PII at rest ───────────────────────────────────────────────────────────────


class PiiAtRestTests(TempDirMixin):
    def test_pii_not_stored_in_plaintext(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        store.create(req)

        json_path = self.base_dir / f"{req.id}.json"
        raw = json_path.read_text(encoding="utf-8")

        # None of the PII must appear verbatim in the JSON file
        for sensitive in [req.name, req.company, req.email, req.motive]:
            self.assertNotIn(sensitive, raw, f"{sensitive!r} found in plaintext on disk")

    def test_pii_readable_with_correct_key_unreadable_with_wrong_key(self) -> None:
        store_correct = _store(self.base_dir, key=KEY)
        store_wrong = _store(self.base_dir, key=OTHER_KEY)

        req = _make()
        store_correct.create(req)

        # Correct key → PII decrypted
        got_correct = store_correct.get(req.id)
        self.assertIsNotNone(got_correct)
        assert got_correct is not None
        self.assertEqual(got_correct.email, req.email)

        # Wrong key → PII fields decrypt to "" fallback (not the real value)
        got_wrong = store_wrong.get(req.id)
        # The store doesn't raise — it returns a record with blank PII or None.
        # Either way, the plaintext email must not be exposed.
        if got_wrong is not None:
            self.assertNotEqual(got_wrong.email, req.email)

    def test_requester_ip_stored_plaintext(self) -> None:
        """IP is not PII in our threat model: it stays unencrypted for indexing."""
        store = _store(self.base_dir)
        req = _make()
        store.create(req)

        json_path = self.base_dir / f"{req.id}.json"
        raw_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(raw_json["requester_ip"], req.requester_ip)

    def test_status_stored_plaintext(self) -> None:
        """Status must be indexable without decryption."""
        store = _store(self.base_dir)
        req = _make()
        store.create(req)

        json_path = self.base_dir / f"{req.id}.json"
        raw_json = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(raw_json["status"], "pending")


# ── Concurrency ───────────────────────────────────────────────────────────────


class ConcurrencyTests(TempDirMixin):
    THREAD_COUNT = 12

    def test_concurrent_creates_all_succeed(self) -> None:
        """Each thread writes its own record; no locking conflict should cause data loss."""
        store = _store(self.base_dir)
        requests: list[AccessRequest] = [_make() for _ in range(self.THREAD_COUNT)]
        errors: list[Exception] = []

        def _create(req: AccessRequest) -> None:
            try:
                store.create(req)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_create, args=(req,)) for req in requests]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"unexpected errors: {errors}")

        for req in requests:
            got = store.get(req.id)
            self.assertIsNotNone(got, f"record {req.id} missing after concurrent create")

    def test_concurrent_reads_on_same_record(self) -> None:
        """Shared locks allow concurrent reads without corruption."""
        store = _store(self.base_dir)
        req = _make()
        store.create(req)

        emails: list[str] = []
        errors: list[Exception] = []

        def _read() -> None:
            try:
                got = store.get(req.id)
                if got is not None:
                    emails.append(got.email)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_read) for _ in range(self.THREAD_COUNT)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"unexpected errors: {errors}")
        self.assertTrue(all(e == req.email for e in emails))


# ── atomic_consume_run ────────────────────────────────────────────────────────


def _approved(now: float | None = None) -> AccessRequest:
    """An AccessRequest already approved with a fresh 24h session window."""
    req = _make()
    req.approve()  # status → APPROVED, session_expires_at set
    return req


class AtomicConsumeRunTests(TempDirMixin):
    def test_first_consume_binds_ip_and_increments(self) -> None:
        store = _store(self.base_dir)
        req = _approved()
        store.create(req)

        result = store.atomic_consume_run(req.id, "9.9.9.9")

        self.assertEqual(result.runs_used, 1)
        self.assertEqual(result.session_ip_binding, "9.9.9.9")
        self.assertEqual(result.status, AccessRequestStatus.APPROVED)
        reloaded = store.get(req.id)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.runs_used, 1)
        self.assertEqual(reloaded.session_ip_binding, "9.9.9.9")

    def test_consume_quota_reaches_consumed_status(self) -> None:
        store = _store(self.base_dir)
        req = _approved()
        store.create(req)

        store.atomic_consume_run(req.id, "9.9.9.9")
        store.atomic_consume_run(req.id, "9.9.9.9")
        result = store.atomic_consume_run(req.id, "9.9.9.9")

        self.assertEqual(result.runs_used, 3)
        self.assertEqual(result.status, AccessRequestStatus.CONSUMED)

    def test_consume_beyond_quota_raises_invalid_transition(self) -> None:
        """Once status flips to CONSUMED, a 4th call sees a non-APPROVED status."""
        store = _store(self.base_dir)
        req = _approved()
        store.create(req)
        for _ in range(3):
            store.atomic_consume_run(req.id, "9.9.9.9")

        with self.assertRaises(InvalidTransition):
            store.atomic_consume_run(req.id, "9.9.9.9")

    def test_ip_mismatch_raises_and_does_not_increment(self) -> None:
        store = _store(self.base_dir)
        req = _approved()
        store.create(req)
        store.atomic_consume_run(req.id, "1.1.1.1")  # binds IP

        with self.assertRaises(IpBindingMismatch):
            store.atomic_consume_run(req.id, "2.2.2.2")

        reloaded = store.get(req.id)
        self.assertEqual(reloaded.runs_used, 1)
        self.assertEqual(reloaded.session_ip_binding, "1.1.1.1")

    def test_consume_on_pending_raises_invalid_transition(self) -> None:
        store = _store(self.base_dir)
        req = _make()  # PENDING
        store.create(req)

        with self.assertRaises(InvalidTransition):
            store.atomic_consume_run(req.id, "9.9.9.9")

    def test_consume_on_rejected_raises_invalid_transition(self) -> None:
        store = _store(self.base_dir)
        req = _make()
        req.reject()
        store.create(req)

        with self.assertRaises(InvalidTransition):
            store.atomic_consume_run(req.id, "9.9.9.9")

    def test_consume_on_revoked_raises_invalid_transition(self) -> None:
        store = _store(self.base_dir)
        req = _approved()
        req.revoke()
        store.create(req)

        with self.assertRaises(InvalidTransition):
            store.atomic_consume_run(req.id, "9.9.9.9")

    def test_unknown_request_id_raises_file_not_found(self) -> None:
        store = _store(self.base_dir)
        with self.assertRaises(FileNotFoundError):
            store.atomic_consume_run("nonexistent", "9.9.9.9")

    def test_empty_ip_raises_value_error(self) -> None:
        store = _store(self.base_dir)
        req = _approved()
        store.create(req)
        with self.assertRaises(ValueError):
            store.atomic_consume_run(req.id, "")

    def test_session_expired_marks_expired_and_raises(self) -> None:
        store = _store(self.base_dir)
        req = _approved()
        req.session_expires_at = time.time() - 1
        store.create(req)

        with self.assertRaises(SessionExpired):
            store.atomic_consume_run(req.id, "9.9.9.9")

        # File persists with status = EXPIRED (so admin views can see history).
        json_path = self.base_dir / f"{req.id}.json"
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["status"], "expired")


class AtomicConsumeRunConcurrencyTests(TempDirMixin):
    def test_concurrent_consume_respects_quota(self) -> None:
        """N threads call atomic_consume_run on the same approved record; quota holds."""
        store = _store(self.base_dir)
        req = _approved()
        req.runs_quota = 3
        store.create(req)

        successes: list[AccessRequest] = []
        failures: list[Exception] = []

        def _consume() -> None:
            try:
                successes.append(store.atomic_consume_run(req.id, "9.9.9.9"))
            except Exception as exc:  # noqa: BLE001
                failures.append(exc)

        threads = [threading.Thread(target=_consume) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 3 successes (quota), the rest are QuotaExceeded or InvalidTransition.
        self.assertEqual(len(successes), 3, f"successes={len(successes)} failures={failures}")
        for exc in failures:
            self.assertIsInstance(exc, (QuotaExceeded, InvalidTransition))

        reloaded = store.get(req.id)
        self.assertEqual(reloaded.runs_used, 3)
        self.assertEqual(reloaded.status, AccessRequestStatus.CONSUMED)


if __name__ == "__main__":
    unittest.main()
