"""Tests for BudgetTracker.

Coverage:
    - first add_tokens creates the day file and returns crossed thresholds
    - alert thresholds fire exactly once per day (idempotence)
    - should_degrade flips at the configured cap
    - get without prior write returns a fresh zero state
    - concurrency: N threads each add tokens, all updates land
    - invalid construction args raise
    - explicit ``day=`` parameter writes to a deterministic file
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from cv_critic_agent.budget.tracker import BudgetTracker, BudgetState


class TempBudgetDir(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="cv-critic-budget-")
        self.base_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class ConstructionTests(TempBudgetDir):
    def test_negative_cap_raises(self) -> None:
        with self.assertRaises(ValueError):
            BudgetTracker(self.base_dir, daily_cap_tokens=0)

    def test_threshold_out_of_range_raises(self) -> None:
        with self.assertRaises(ValueError):
            BudgetTracker(self.base_dir, daily_cap_tokens=100, alert_thresholds=(101,))
        with self.assertRaises(ValueError):
            BudgetTracker(self.base_dir, daily_cap_tokens=100, alert_thresholds=(0,))

    def test_base_dir_created_if_missing(self) -> None:
        new_dir = self.base_dir / "nested" / "budget"
        BudgetTracker(new_dir, daily_cap_tokens=100)
        self.assertTrue(new_dir.exists())


class GetTests(TempBudgetDir):
    def test_get_without_write_returns_zero(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        state = tracker.get(day="2026-06-08")
        self.assertEqual(state.tokens_used, 0)
        self.assertEqual(state.alerts_sent, [])
        self.assertEqual(state.date, "2026-06-08")

    def test_get_reads_back_persisted_state(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(500, day="2026-06-08")
        state = tracker.get(day="2026-06-08")
        self.assertEqual(state.tokens_used, 500)


class AddTokensTests(TempBudgetDir):
    def test_first_add_persists_count_and_returns_no_alerts(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000, alert_thresholds=(80, 100))
        state, new_alerts = tracker.add_tokens(100, day="2026-06-08")
        self.assertEqual(state.tokens_used, 100)
        self.assertEqual(new_alerts, [])

    def test_negative_n_raises(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        with self.assertRaises(ValueError):
            tracker.add_tokens(-1)

    def test_zero_n_persists_without_creating_alerts(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        state, alerts = tracker.add_tokens(0, day="2026-06-08")
        self.assertEqual(state.tokens_used, 0)
        self.assertEqual(alerts, [])

    def test_crossing_80_percent_returns_alert_once(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000, alert_thresholds=(80, 100))
        _, first = tracker.add_tokens(800, day="2026-06-08")
        self.assertEqual(first, [80])
        _, second = tracker.add_tokens(50, day="2026-06-08")
        self.assertEqual(second, [])

    def test_crossing_80_and_100_in_single_add_returns_both(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000, alert_thresholds=(80, 100))
        _, alerts = tracker.add_tokens(1500, day="2026-06-08")
        self.assertEqual(alerts, [80, 100])

    def test_crossing_100_first_does_not_skip_80(self) -> None:
        """If we jump straight past the cap, both thresholds fire."""
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        _, alerts = tracker.add_tokens(2000, day="2026-06-08")
        self.assertEqual(alerts, [80, 100])

    def test_alerts_are_persisted_across_calls(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(900, day="2026-06-08")
        # New tracker instance reads same dir.
        other = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        state = other.get(day="2026-06-08")
        self.assertEqual(state.alerts_sent, [80])

    def test_different_days_track_independently(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(500, day="2026-06-08")
        tracker.add_tokens(200, day="2026-06-09")
        self.assertEqual(tracker.get(day="2026-06-08").tokens_used, 500)
        self.assertEqual(tracker.get(day="2026-06-09").tokens_used, 200)


class ShouldDegradeTests(TempBudgetDir):
    def test_below_cap_does_not_degrade(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(999, day="2026-06-08")
        self.assertFalse(tracker.should_degrade(day="2026-06-08"))

    def test_at_cap_degrades(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(1000, day="2026-06-08")
        self.assertTrue(tracker.should_degrade(day="2026-06-08"))

    def test_above_cap_degrades(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(1500, day="2026-06-08")
        self.assertTrue(tracker.should_degrade(day="2026-06-08"))


class PersistenceFormatTests(TempBudgetDir):
    def test_file_format_is_plain_json(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        tracker.add_tokens(100, day="2026-06-08")
        raw = json.loads((self.base_dir / "2026-06-08.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["tokens_used"], 100)
        self.assertEqual(raw["alerts_sent"], [])

    def test_corrupted_file_get_returns_zero(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=1000)
        (self.base_dir / "2026-06-08.json").write_text("garbage")
        state = tracker.get(day="2026-06-08")
        self.assertEqual(state.tokens_used, 0)


class ConcurrencyTests(TempBudgetDir):
    def test_concurrent_adds_sum_correctly(self) -> None:
        tracker = BudgetTracker(self.base_dir, daily_cap_tokens=10_000)

        def _add() -> None:
            tracker.add_tokens(100, day="2026-06-08")

        threads = [threading.Thread(target=_add) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(tracker.get(day="2026-06-08").tokens_used, 2_000)


if __name__ == "__main__":
    unittest.main()
