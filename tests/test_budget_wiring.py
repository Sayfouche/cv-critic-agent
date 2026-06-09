"""Tests for budget.wiring.record_real_run.

Coverage:
    - happy path: tokens add, threshold crosses, alert fires with right payload
    - no threshold crossed → zero notifier calls
    - missing bot_token / owner_chat_id → tracker still increments, zero calls
    - notifier returns False → state unchanged, alerts_fired empty
    - both thresholds cross in one shot → two alerts fired in order
    - idempotence: second call below the next threshold → no new alerts
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

import httpx

from cv_critic_agent.budget.tracker import BudgetTracker
from cv_critic_agent.budget.wiring import record_real_run

# ── Async mock primitives (mirrors test_notifier.py) ─────────────────────────


class _MockResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_data if json_data is not None else {"ok": True}

    def json(self) -> dict:
        return self._json


class _RecordingClient:
    def __init__(
        self,
        response: _MockResponse | None = None,
        raises: Exception | None = None,
    ) -> None:
        self.response = response or _MockResponse()
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> _RecordingClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> _MockResponse:
        self.calls.append({"url": url, "json": kwargs.get("json")})
        if self.raises:
            raise self.raises
        return self.response


def _factory(client: _RecordingClient):
    def make_client(*_args: Any, **_kwargs: Any) -> _RecordingClient:
        return client

    return make_client


# ── Fixtures ─────────────────────────────────────────────────────────────────


class _BudgetFixture(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="cv-critic-wiring-")
        self.tracker = BudgetTracker(
            Path(self._tmp.name),
            daily_cap_tokens=1000,
            alert_thresholds=(80, 100),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()


# ── Happy path: threshold crosses → one alert ────────────────────────────────


class HappyPathTests(_BudgetFixture):
    async def test_below_threshold_no_alert(self) -> None:
        client = _RecordingClient()
        state, fired = await record_real_run(
            self.tracker,
            500,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(state.tokens_used, 500)
        self.assertEqual(fired, [])
        self.assertEqual(client.calls, [])

    async def test_crossing_eighty_fires_one_alert(self) -> None:
        client = _RecordingClient()
        state, fired = await record_real_run(
            self.tracker,
            800,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(state.tokens_used, 800)
        self.assertEqual(fired, [80])
        self.assertEqual(len(client.calls), 1)
        text = client.calls[0]["json"]["text"]
        self.assertIn("80%", text)
        self.assertIn("800", text)

    async def test_crossing_both_thresholds_in_one_shot_fires_two_alerts(self) -> None:
        client = _RecordingClient()
        state, fired = await record_real_run(
            self.tracker,
            1500,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(state.tokens_used, 1500)
        self.assertEqual(fired, [80, 100])
        self.assertEqual(len(client.calls), 2)
        self.assertIn("80%", client.calls[0]["json"]["text"])
        self.assertIn("100%", client.calls[1]["json"]["text"])


# ── Idempotence: a threshold fires exactly once per day ──────────────────────


class IdempotenceTests(_BudgetFixture):
    async def test_second_call_below_next_threshold_does_not_re_fire(self) -> None:
        client = _RecordingClient()
        await record_real_run(
            self.tracker,
            800,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        # Second call stays under 100% — only the 80% alert was due, already sent.
        _, fired = await record_real_run(
            self.tracker,
            50,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(fired, [])
        self.assertEqual(len(client.calls), 1)


# ── Missing notifier config: tracker still records, no notifier call ─────────


class MissingNotifierConfigTests(_BudgetFixture):
    async def test_missing_bot_token_skips_notifier(self) -> None:
        client = _RecordingClient()
        state, fired = await record_real_run(
            self.tracker,
            1500,
            bot_token="",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(state.tokens_used, 1500)  # still recorded
        self.assertEqual(fired, [])
        self.assertEqual(client.calls, [])

    async def test_missing_chat_id_skips_notifier(self) -> None:
        client = _RecordingClient()
        _, fired = await record_real_run(
            self.tracker,
            1500,
            bot_token="bot-token",
            owner_chat_id="",
            http_client_factory=_factory(client),
        )
        self.assertEqual(fired, [])
        self.assertEqual(client.calls, [])


# ── Fail-soft on notifier error: alert marked sent in tracker either way ─────


class NotifierFailureTests(_BudgetFixture):
    async def test_notifier_network_error_returns_empty_fired_list(self) -> None:
        client = _RecordingClient(raises=httpx.ReadTimeout("slow"))
        state, fired = await record_real_run(
            self.tracker,
            800,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        # Tracker has marked 80 as sent (it's the side that owns idempotence);
        # wiring reports empty fired list because the network call failed.
        self.assertIn(80, state.alerts_sent)
        self.assertEqual(fired, [])

    async def test_notifier_returns_false_yields_empty_fired_list(self) -> None:
        client = _RecordingClient(response=_MockResponse(200, {"ok": False}))
        _, fired = await record_real_run(
            self.tracker,
            800,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(fired, [])
        self.assertEqual(len(client.calls), 1)


# ── Zero tokens: no-op alert path even if threshold list non-empty ───────────


class ZeroTokensTests(_BudgetFixture):
    async def test_zero_tokens_no_alert_no_notifier_call(self) -> None:
        client = _RecordingClient()
        state, fired = await record_real_run(
            self.tracker,
            0,
            bot_token="bot-token",
            owner_chat_id=42,
            http_client_factory=_factory(client),
        )
        self.assertEqual(state.tokens_used, 0)
        self.assertEqual(fired, [])
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
