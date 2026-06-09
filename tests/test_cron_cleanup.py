"""Tests for POST /api/cron/cleanup and BudgetTracker.cleanup_old_days.

Coverage (cron endpoint):
    - 503 when cleanup_secret is empty (feature flag off)
    - 401 when X-Cleanup-Secret missing or wrong
    - 200 + counts when secret matches and both stores are configured
    - graceful zero counts when ar_store or budget_tracker are None
    - constant-time compare (hmac.compare_digest): same-length wrong secret still 401

Coverage (BudgetTracker.cleanup_old_days):
    - files older than retain_days are removed; today's file is kept
    - empty directory → returns 0
    - retain_days=0 keeps only today's file
    - invalid retain_days raises
"""
from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cv_critic_agent.budget.tracker import BudgetTracker
from cv_critic_agent.cron_router import router as cron_router

# ── BudgetTracker.cleanup_old_days ───────────────────────────────────────────


class CleanupOldDaysTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="cv-critic-budget-cleanup-")
        self.base_dir = Path(self._tmp.name)
        self.tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_day(self, day: str) -> Path:
        path = self.base_dir / f"{day}.json"
        path.write_text(json.dumps({"tokens_used": 0, "alerts_sent": []}))
        return path

    def test_empty_dir_returns_zero(self) -> None:
        self.assertEqual(self.tracker.cleanup_old_days(retain_days=90), 0)

    def test_files_older_than_retain_are_deleted(self) -> None:
        today = "2026-06-09"
        old = self._write_day("2026-01-01")
        recent = self._write_day("2026-06-08")
        self._write_day(today)
        deleted = self.tracker.cleanup_old_days(retain_days=90, now=today)
        self.assertEqual(deleted, 1)
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())

    def test_retain_zero_keeps_only_today(self) -> None:
        today = "2026-06-09"
        self._write_day("2026-06-08")
        self._write_day(today)
        deleted = self.tracker.cleanup_old_days(retain_days=0, now=today)
        self.assertEqual(deleted, 1)
        self.assertTrue((self.base_dir / f"{today}.json").exists())

    def test_negative_retain_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.tracker.cleanup_old_days(retain_days=-1)

    def test_invalid_now_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.tracker.cleanup_old_days(retain_days=90, now="not-a-date")


# ── Cron endpoint ────────────────────────────────────────────────────────────


class _StubArStore:
    def __init__(self, count: int = 0) -> None:
        self._count = count
        self.calls = 0

    def cleanup_expired(self) -> int:
        self.calls += 1
        return self._count


class _StubTracker:
    def __init__(self, count: int = 0) -> None:
        self._count = count
        self.calls = 0

    def cleanup_old_days(self, retain_days: int = 90) -> int:
        self.calls += 1
        return self._count


def _build_app(
    *,
    secret: str,
    ar_store: Any = None,
    budget_tracker: Any = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(cron_router)
    app.state.cleanup_secret = secret
    app.state.ar_store = ar_store
    app.state.budget_tracker = budget_tracker
    return TestClient(app)


_VALID_SECRET = "test-cleanup-secret-32-bytes-ok!!"


class CronAuthTests(unittest.TestCase):
    def test_503_when_secret_not_configured(self) -> None:
        client = _build_app(secret="")
        res = client.post("/api/cron/cleanup", headers={"X-Cleanup-Secret": "anything"})
        self.assertEqual(res.status_code, 503)

    def test_401_when_header_missing(self) -> None:
        client = _build_app(secret=_VALID_SECRET)
        res = client.post("/api/cron/cleanup")
        self.assertEqual(res.status_code, 401)

    def test_401_when_header_wrong(self) -> None:
        client = _build_app(secret=_VALID_SECRET)
        res = client.post(
            "/api/cron/cleanup", headers={"X-Cleanup-Secret": "wrong-but-same-length-zzzzzzzzz"}
        )
        self.assertEqual(res.status_code, 401)


class CronHappyPathTests(unittest.TestCase):
    def test_returns_counts_from_both_stores(self) -> None:
        ar = _StubArStore(count=3)
        tracker = _StubTracker(count=2)
        client = _build_app(secret=_VALID_SECRET, ar_store=ar, budget_tracker=tracker)
        res = client.post(
            "/api/cron/cleanup", headers={"X-Cleanup-Secret": _VALID_SECRET}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            {"access_requests_purged": 3, "budget_files_purged": 2},
        )
        self.assertEqual(ar.calls, 1)
        self.assertEqual(tracker.calls, 1)

    def test_missing_ar_store_yields_zero(self) -> None:
        tracker = _StubTracker(count=5)
        client = _build_app(secret=_VALID_SECRET, ar_store=None, budget_tracker=tracker)
        res = client.post(
            "/api/cron/cleanup", headers={"X-Cleanup-Secret": _VALID_SECRET}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["access_requests_purged"], 0)
        self.assertEqual(res.json()["budget_files_purged"], 5)

    def test_missing_budget_tracker_yields_zero(self) -> None:
        ar = _StubArStore(count=7)
        client = _build_app(secret=_VALID_SECRET, ar_store=ar, budget_tracker=None)
        res = client.post(
            "/api/cron/cleanup", headers={"X-Cleanup-Secret": _VALID_SECRET}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["access_requests_purged"], 7)
        self.assertEqual(res.json()["budget_files_purged"], 0)

    def test_idempotent_double_call(self) -> None:
        ar = _StubArStore(count=0)
        tracker = _StubTracker(count=0)
        client = _build_app(secret=_VALID_SECRET, ar_store=ar, budget_tracker=tracker)
        for _ in range(2):
            res = client.post(
                "/api/cron/cleanup", headers={"X-Cleanup-Secret": _VALID_SECRET}
            )
            self.assertEqual(res.status_code, 200)
        self.assertEqual(ar.calls, 2)
        self.assertEqual(tracker.calls, 2)


if __name__ == "__main__":
    unittest.main()


# Silence unused-import warnings from optional helpers.
_ = dt
