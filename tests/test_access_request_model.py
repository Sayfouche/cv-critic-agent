"""State-machine tests for AccessRequest.

Each section pins one transition rule. We never test that "approve sets
status to APPROVED" without also testing "approve from a non-PENDING state
raises" — the rule is the pair.
"""
from __future__ import annotations

import time
import unittest

from cv_critic_agent.access_requests.models import (
    DECIDED_TTL_SECONDS,
    PENDING_TTL_SECONDS,
    AccessRequest,
    AccessRequestStatus,
    InvalidTransition,
    IpBindingMismatch,
    QuotaExceeded,
)


def _make() -> AccessRequest:
    return AccessRequest.new(
        name="Alice",
        company="ACME",
        email="alice@example.com",
        motive="evaluating CV Critic Agent",
        requester_ip="1.2.3.4",
    )


class CreationTests(unittest.TestCase):
    def test_factory_initializes_status_pending(self) -> None:
        self.assertEqual(_make().status, AccessRequestStatus.PENDING)

    def test_factory_assigns_unique_ids(self) -> None:
        ids = {_make().id for _ in range(10)}
        self.assertEqual(len(ids), 10)

    def test_factory_records_creation_time_now(self) -> None:
        r = _make()
        self.assertAlmostEqual(r.created_at, time.time(), delta=2.0)


class ApproveTests(unittest.TestCase):
    def test_approve_sets_status_and_timestamps(self) -> None:
        r = _make()
        r.approve()
        self.assertEqual(r.status, AccessRequestStatus.APPROVED)
        self.assertIsNotNone(r.decided_at)
        self.assertIsNotNone(r.session_expires_at)

    def test_double_approve_rejected(self) -> None:
        r = _make()
        r.approve()
        with self.assertRaises(InvalidTransition):
            r.approve()

    def test_approve_after_reject_rejected(self) -> None:
        r = _make()
        r.reject()
        with self.assertRaises(InvalidTransition):
            r.approve()


class RejectTests(unittest.TestCase):
    def test_reject_sets_status_and_timestamp(self) -> None:
        r = _make()
        r.reject()
        self.assertEqual(r.status, AccessRequestStatus.REJECTED)
        self.assertIsNotNone(r.decided_at)

    def test_reject_after_approve_rejected(self) -> None:
        r = _make()
        r.approve()
        with self.assertRaises(InvalidTransition):
            r.reject()


class ConsumeRunTests(unittest.TestCase):
    def test_first_consume_increments_quota(self) -> None:
        r = _make()
        r.approve()
        r.consume_one_run()
        self.assertEqual(r.runs_used, 1)
        self.assertEqual(r.status, AccessRequestStatus.APPROVED)

    def test_last_consume_flips_to_consumed(self) -> None:
        r = _make()
        r.approve()
        for _ in range(r.runs_quota):
            r.consume_one_run()
        self.assertEqual(r.status, AccessRequestStatus.CONSUMED)

    def test_consume_beyond_quota_rejected_via_state_machine(self) -> None:
        # After exhaustion the status auto-flips to CONSUMED, so the next call
        # hits the state-machine guard first. This is the path real callers see.
        r = _make()
        r.approve()
        for _ in range(r.runs_quota):
            r.consume_one_run()
        with self.assertRaises(InvalidTransition):
            r.consume_one_run()

    def test_quota_exceeded_when_state_is_inconsistent(self) -> None:
        # Defensive guard: a corrupted store could yield runs_used >= runs_quota
        # while status is still APPROVED. QuotaExceeded fires before the
        # increment, so we never silently overshoot.
        r = _make()
        r.approve()
        r.runs_used = r.runs_quota
        with self.assertRaises(QuotaExceeded):
            r.consume_one_run()

    def test_consume_pending_rejected(self) -> None:
        with self.assertRaises(InvalidTransition):
            _make().consume_one_run()


class IpBindingTests(unittest.TestCase):
    def test_first_call_sets_binding(self) -> None:
        r = _make()
        r.approve()
        r.bind_ip("1.2.3.4")
        self.assertEqual(r.session_ip_binding, "1.2.3.4")

    def test_same_ip_passes_idempotently(self) -> None:
        r = _make()
        r.approve()
        r.bind_ip("1.2.3.4")
        r.bind_ip("1.2.3.4")  # no exception
        self.assertEqual(r.session_ip_binding, "1.2.3.4")

    def test_different_ip_raises(self) -> None:
        r = _make()
        r.approve()
        r.bind_ip("1.2.3.4")
        with self.assertRaises(IpBindingMismatch):
            r.bind_ip("5.6.7.8")

    def test_empty_ip_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _make().bind_ip("")


class RevokeTests(unittest.TestCase):
    def test_revoke_from_approved(self) -> None:
        r = _make()
        r.approve()
        r.revoke()
        self.assertEqual(r.status, AccessRequestStatus.REVOKED)

    def test_revoke_pending_rejected(self) -> None:
        with self.assertRaises(InvalidTransition):
            _make().revoke()

    def test_revoke_idempotent(self) -> None:
        r = _make()
        r.approve()
        r.revoke()
        r.revoke()  # no exception
        self.assertEqual(r.status, AccessRequestStatus.REVOKED)


class ExpiryTests(unittest.TestCase):
    def test_mark_expired_noop_on_terminal_status(self) -> None:
        r = _make()
        r.reject()
        r.mark_expired()
        self.assertEqual(r.status, AccessRequestStatus.REJECTED)

    def test_mark_expired_moves_pending_to_expired(self) -> None:
        r = _make()
        r.mark_expired()
        self.assertEqual(r.status, AccessRequestStatus.EXPIRED)

    def test_pending_expired_after_ttl(self) -> None:
        r = _make()
        future = time.time() + PENDING_TTL_SECONDS + 1
        self.assertTrue(r.is_pending_expired(now=future))

    def test_pending_not_expired_within_ttl(self) -> None:
        r = _make()
        self.assertFalse(r.is_pending_expired())

    def test_decided_purgeable_after_ttl(self) -> None:
        r = _make()
        r.reject()
        future = time.time() + DECIDED_TTL_SECONDS + 1
        self.assertTrue(r.is_decided_purgeable(now=future))

    def test_decided_not_purgeable_just_after_decision(self) -> None:
        r = _make()
        r.reject()
        self.assertFalse(r.is_decided_purgeable())


class SessionPredicateTests(unittest.TestCase):
    def test_session_valid_just_after_approval(self) -> None:
        r = _make()
        r.approve()
        self.assertTrue(r.is_session_valid())

    def test_session_invalid_when_pending(self) -> None:
        self.assertFalse(_make().is_session_valid())

    def test_session_invalid_when_rejected(self) -> None:
        r = _make()
        r.reject()
        self.assertFalse(r.is_session_valid())

    def test_session_invalid_when_quota_exhausted(self) -> None:
        r = _make()
        r.approve()
        for _ in range(r.runs_quota):
            r.consume_one_run()
        self.assertFalse(r.is_session_valid())

    def test_session_invalid_after_expiry(self) -> None:
        r = _make()
        r.approve()
        assert r.session_expires_at is not None
        far_future = r.session_expires_at + 1
        self.assertFalse(r.is_session_valid(now=far_future))


if __name__ == "__main__":
    unittest.main()
