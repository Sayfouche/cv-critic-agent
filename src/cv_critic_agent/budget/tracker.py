"""Daily token-budget tracker for real LLM runs.

One JSON file per UTC day: ``<base_dir>/<YYYY-MM-DD>.json``. Each file holds
the cumulative output-token count and the list of alert thresholds that
have already been notified (so a Telegram alert at 80 % fires exactly once).

The tracker is the single place that decides "the real-mode budget is
spent": ``should_degrade()`` returns True once the cap is reached, and the
caller silently falls back to a mock run (Phase 5 spec §5).

Concurrency
-----------
``add_tokens`` opens the day file with ``LOCK_EX``, so two concurrent
recorders cannot lose updates. The lock is held only for the duration of
the read-modify-write; reading via ``get`` uses ``LOCK_SH``.

Time zone
---------
Days are bounded by UTC, not local time. This keeps the rollover behaviour
identical across server time zones.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BudgetState:
    """Snapshot of one day's budget consumption."""

    date: str  # ISO YYYY-MM-DD (UTC)
    tokens_used: int = 0
    alerts_sent: list[int] = field(default_factory=list)  # threshold percents (e.g. 80, 100)


class BudgetTracker:
    """Daily output-token meter with idempotent alert thresholds.

    Parameters
    ----------
    base_dir:
        Directory where one JSON file per day is written. Created on init.
    daily_cap_tokens:
        Hard cap. ``should_degrade()`` returns True once
        ``tokens_used >= daily_cap_tokens``.
    alert_thresholds:
        Percentages (1..100) at which the next ``add_tokens`` call returns
        a "new alert" so the caller can send a Telegram notification.
        Each threshold fires exactly once per day.
    """

    def __init__(
        self,
        base_dir: Path,
        daily_cap_tokens: int,
        alert_thresholds: tuple[int, ...] = (80, 100),
    ) -> None:
        if daily_cap_tokens <= 0:
            raise ValueError("daily_cap_tokens must be > 0")
        for pct in alert_thresholds:
            if not 1 <= pct <= 100:
                raise ValueError(f"alert threshold {pct} must be in 1..100")
        self._base_dir = Path(base_dir)
        self._cap = int(daily_cap_tokens)
        self._thresholds = tuple(sorted(alert_thresholds))
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ──────────────────────────────────────────────────────────

    def get(self, day: str | None = None) -> BudgetState:
        """Read today's (or *day*'s) snapshot. Returns a fresh zero state if
        the file does not exist yet — no side effects."""
        day = day or _today_utc()
        path = self._path(day)
        if not path.exists():
            return BudgetState(date=day)
        try:
            with path.open("r", encoding="utf-8") as fh:
                fcntl.flock(fh, fcntl.LOCK_SH)
                try:
                    data = json.load(fh)
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        except (OSError, json.JSONDecodeError):
            return BudgetState(date=day)
        return BudgetState(
            date=day,
            tokens_used=int(data.get("tokens_used", 0)),
            alerts_sent=list(data.get("alerts_sent", [])),
        )

    def add_tokens(self, n: int, day: str | None = None) -> tuple[BudgetState, list[int]]:
        """Increment today's counter by *n*. Atomic.

        Returns the post-write ``BudgetState`` and the list of alert
        threshold percentages that just got crossed for the first time
        today (the caller should send one Telegram alert per item).

        ``n`` must be a non-negative int.
        """
        if n < 0:
            raise ValueError("n must be >= 0")
        day = day or _today_utc()
        path = self._path(day)
        # ``a+`` creates the file if missing without truncating an existing
        # one — so the "create + lock + read + write" sequence happens under
        # a single file descriptor and one ``LOCK_EX``, race-free.
        with path.open("a+", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                raw = fh.read()
                try:
                    data = json.loads(raw) if raw else {"tokens_used": 0, "alerts_sent": []}
                except json.JSONDecodeError:
                    data = {"tokens_used": 0, "alerts_sent": []}
                before = int(data.get("tokens_used", 0))
                alerts_before: list[int] = list(data.get("alerts_sent", []))
                after = before + n

                new_alerts: list[int] = []
                for pct in self._thresholds:
                    if pct in alerts_before:
                        continue
                    crossed_amount = self._cap * pct // 100
                    if after >= crossed_amount:
                        new_alerts.append(pct)

                alerts_after = sorted(set(alerts_before + new_alerts))
                payload = {"tokens_used": after, "alerts_sent": alerts_after}
                fh.seek(0)
                fh.truncate()
                fh.write(json.dumps(payload, ensure_ascii=False))
                # Flush Python's buffer before releasing the lock so the next
                # waiter reads the updated bytes, not the stale ones still in
                # the buffer (manifested as off-by-one totals in concurrent
                # add_tokens tests).
                fh.flush()
                return (
                    BudgetState(date=day, tokens_used=after, alerts_sent=alerts_after),
                    new_alerts,
                )
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def should_degrade(self, day: str | None = None) -> bool:
        """True once today's usage hits or exceeds the daily cap."""
        return self.get(day).tokens_used >= self._cap

    def cleanup_old_days(self, retain_days: int = 90, now: str | None = None) -> int:
        """Delete per-day JSON files older than *retain_days* days.

        Day comparison is lexicographic on the YYYY-MM-DD filename (since
        days are UTC). Returns the count of files deleted. A negative
        ``retain_days`` raises ``ValueError`` to surface accidental misuse.
        """
        if retain_days < 0:
            raise ValueError("retain_days must be >= 0")
        today = now or _today_utc()
        try:
            cutoff_dt = dt.datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=dt.UTC)
        except ValueError as exc:
            raise ValueError(f"invalid now date {today!r}") from exc
        cutoff_str = (cutoff_dt - dt.timedelta(days=retain_days)).strftime("%Y-%m-%d")
        count = 0
        for path in self._base_dir.glob("*.json"):
            if path.stem < cutoff_str:
                try:
                    path.unlink()
                    count += 1
                except OSError:
                    continue
        return count

    @property
    def daily_cap(self) -> int:
        return self._cap

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _path(self, day: str) -> Path:
        return self._base_dir / f"{day}.json"


def _today_utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
