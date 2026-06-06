"""Tests for the notifier layer — Telegram + Resend.

Same _MockAsyncClient injection pattern as test_security_middleware.py.
We pin every realistic failure mode (network error, non-200, malformed
JSON, ok=False) plus the four happy-path payload shapes from the Phase 5
plan: owner pending, requester approved, requester rejected, budget alert.
"""
from __future__ import annotations

import unittest
from typing import Any

import httpx

from cv_critic_agent.notifier.email import (
    RESEND_SEND_URL,
    send_requester_approved,
    send_requester_rejected,
)
from cv_critic_agent.notifier.telegram import (
    is_owner_callback,
    send_budget_alert,
    send_owner_pending,
)

# ── Async mock primitives (mirrors test_security_middleware.py) ───────────────


class _MockResponse:
    def __init__(self, status_code: int, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_data

    def json(self) -> dict:
        if self._json is None:
            raise ValueError("response has no JSON body")
        return self._json


class _RecordingClient:
    """Async mock that captures every POST call's url/json/headers."""

    def __init__(
        self,
        response: _MockResponse | None = None,
        raises: Exception | None = None,
    ) -> None:
        self.response = response or _MockResponse(200, {"ok": True})
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> _RecordingClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> _MockResponse:
        self.calls.append({"url": url, "json": kwargs.get("json"), "headers": kwargs.get("headers")})
        if self.raises:
            raise self.raises
        return self.response


def _factory(client: _RecordingClient):
    """Return an http_client_factory that always yields the given client."""

    def _make(**_kwargs: object) -> _RecordingClient:
        return client

    return _make


# ── Telegram: send_owner_pending ──────────────────────────────────────────────


class SendOwnerPendingTests(unittest.IsolatedAsyncioTestCase):
    async def _send(self, client: _RecordingClient) -> bool:
        return await send_owner_pending(
            bot_token="bot-token",
            owner_chat_id=999_000,
            request_id="req-abc",
            name="Alice",
            company="ACME Corp",
            motive="testing the agent",
            approve_url="https://api.example.com/decide?token=A&accept=1",
            reject_url="https://api.example.com/decide?token=A&accept=0",
            http_client_factory=_factory(client),
        )

    async def test_happy_path_returns_true(self) -> None:
        client = _RecordingClient()
        self.assertTrue(await self._send(client))

    async def test_posts_to_send_message_endpoint_with_bot_token(self) -> None:
        client = _RecordingClient()
        await self._send(client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(
            client.calls[0]["url"],
            "https://api.telegram.org/botbot-token/sendMessage",
        )

    async def test_payload_includes_chat_id_and_markdown_parse_mode(self) -> None:
        client = _RecordingClient()
        await self._send(client)
        body = client.calls[0]["json"]
        self.assertEqual(body["chat_id"], 999_000)
        self.assertEqual(body["parse_mode"], "Markdown")

    async def test_text_contains_name_company_motive_request_id(self) -> None:
        client = _RecordingClient()
        await self._send(client)
        text = client.calls[0]["json"]["text"]
        for needle in ("Alice", "ACME Corp", "testing the agent", "req-abc"):
            self.assertIn(needle, text)

    async def test_inline_keyboard_carries_both_urls(self) -> None:
        client = _RecordingClient()
        await self._send(client)
        keyboard = client.calls[0]["json"]["reply_markup"]["inline_keyboard"]
        row = keyboard[0]
        urls = {button["url"] for button in row}
        self.assertEqual(
            urls,
            {
                "https://api.example.com/decide?token=A&accept=1",
                "https://api.example.com/decide?token=A&accept=0",
            },
        )

    async def test_network_error_returns_false(self) -> None:
        client = _RecordingClient(raises=httpx.ConnectError("net down"))
        self.assertFalse(await self._send(client))

    async def test_non_200_returns_false(self) -> None:
        client = _RecordingClient(response=_MockResponse(500, {}))
        self.assertFalse(await self._send(client))

    async def test_ok_false_returns_false(self) -> None:
        client = _RecordingClient(response=_MockResponse(200, {"ok": False, "description": "bad chat_id"}))
        self.assertFalse(await self._send(client))

    async def test_malformed_json_returns_false(self) -> None:
        client = _RecordingClient(response=_MockResponse(200, None))
        self.assertFalse(await self._send(client))


# ── Telegram: send_budget_alert ───────────────────────────────────────────────


class SendBudgetAlertTests(unittest.IsolatedAsyncioTestCase):
    async def _send(self, client: _RecordingClient, percentage: int) -> bool:
        return await send_budget_alert(
            bot_token="bot-token",
            owner_chat_id=42,
            percentage=percentage,
            tokens_used=160_000,
            daily_cap=200_000,
            http_client_factory=_factory(client),
        )

    async def test_eighty_percent_uses_warning_severity(self) -> None:
        client = _RecordingClient()
        await self._send(client, 80)
        text = client.calls[0]["json"]["text"]
        self.assertIn("Budget warning", text)
        self.assertIn("80%", text)
        self.assertNotIn("degrade to mock", text)

    async def test_hundred_percent_uses_cap_hit_and_mentions_degrade(self) -> None:
        client = _RecordingClient()
        await self._send(client, 100)
        text = client.calls[0]["json"]["text"]
        self.assertIn("Budget cap hit", text)
        self.assertIn("100%", text)
        self.assertIn("degrade to mock", text)

    async def test_tokens_used_and_cap_are_formatted_with_commas(self) -> None:
        client = _RecordingClient()
        await self._send(client, 80)
        text = client.calls[0]["json"]["text"]
        self.assertIn("160,000", text)
        self.assertIn("200,000", text)

    async def test_network_error_returns_false(self) -> None:
        client = _RecordingClient(raises=httpx.ReadTimeout("slow"))
        self.assertFalse(await self._send(client, 100))


# ── Telegram: is_owner_callback ───────────────────────────────────────────────


class IsOwnerCallbackTests(unittest.TestCase):
    def test_matching_int_returns_true(self) -> None:
        self.assertTrue(is_owner_callback(12345, 12345))

    def test_matching_int_vs_string_returns_true(self) -> None:
        # Telegram payloads can deserialise as int; env vars come as strings.
        self.assertTrue(is_owner_callback(12345, "12345"))

    def test_different_id_returns_false(self) -> None:
        self.assertFalse(is_owner_callback(99999, 12345))

    def test_none_from_id_returns_false(self) -> None:
        self.assertFalse(is_owner_callback(None, 12345))

    def test_empty_owner_chat_id_returns_false(self) -> None:
        # Defensive: misconfigured server must reject everyone, not let everyone in.
        self.assertFalse(is_owner_callback(12345, ""))


# ── Resend: send_requester_approved ───────────────────────────────────────────


class SendRequesterApprovedTests(unittest.IsolatedAsyncioTestCase):
    async def _send(self, client: _RecordingClient) -> bool:
        return await send_requester_approved(
            api_key="re_test_key",
            from_address="agent@cv-critic.example.com",
            to_address="alice@example.com",
            requester_name="Alice",
            session_url="https://agentic-ai.example.com/access-granted/sess-token",
            runs_quota=3,
            session_expires_in_hours=24,
            http_client_factory=_factory(client),
        )

    async def test_happy_path_returns_true(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        self.assertTrue(await self._send(client))

    async def test_posts_to_resend_endpoint(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        await self._send(client)
        self.assertEqual(client.calls[0]["url"], RESEND_SEND_URL)

    async def test_bearer_auth_header_uses_api_key(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        await self._send(client)
        self.assertEqual(client.calls[0]["headers"]["Authorization"], "Bearer re_test_key")

    async def test_to_field_is_list_with_recipient(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        await self._send(client)
        body = client.calls[0]["json"]
        self.assertEqual(body["from"], "agent@cv-critic.example.com")
        self.assertEqual(body["to"], ["alice@example.com"])

    async def test_subject_mentions_approval(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        await self._send(client)
        self.assertIn("approved", client.calls[0]["json"]["subject"].lower())

    async def test_text_and_html_contain_session_url_and_quota(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        await self._send(client)
        body = client.calls[0]["json"]
        for field in ("text", "html"):
            self.assertIn("Alice", body[field])
            self.assertIn("https://agentic-ai.example.com/access-granted/sess-token", body[field])
            self.assertIn("3", body[field])
            self.assertIn("24", body[field])

    async def test_html_contains_anchor_tag(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-1"}))
        await self._send(client)
        self.assertIn("<a href=", client.calls[0]["json"]["html"])

    async def test_non_2xx_returns_false(self) -> None:
        client = _RecordingClient(response=_MockResponse(401, {"name": "validation_error"}))
        self.assertFalse(await self._send(client))

    async def test_network_error_returns_false(self) -> None:
        client = _RecordingClient(raises=httpx.ConnectError("DNS"))
        self.assertFalse(await self._send(client))


# ── Resend: send_requester_rejected ───────────────────────────────────────────


class SendRequesterRejectedTests(unittest.IsolatedAsyncioTestCase):
    async def _send(self, client: _RecordingClient) -> bool:
        return await send_requester_rejected(
            api_key="re_test_key",
            from_address="agent@cv-critic.example.com",
            to_address="bob@example.com",
            requester_name="Bob",
            http_client_factory=_factory(client),
        )

    async def test_happy_path_returns_true(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-2"}))
        self.assertTrue(await self._send(client))

    async def test_subject_does_not_say_approved_or_rejected(self) -> None:
        # Polite framing: subject must not shout "REJECTED" in the inbox preview.
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-2"}))
        await self._send(client)
        subject = client.calls[0]["json"]["subject"].lower()
        self.assertNotIn("rejected", subject)
        self.assertNotIn("denied", subject)

    async def test_body_mentions_mock_demo_path(self) -> None:
        client = _RecordingClient(response=_MockResponse(202, {"id": "msg-2"}))
        await self._send(client)
        body = client.calls[0]["json"]
        for field in ("text", "html"):
            self.assertIn("Bob", body[field])
            self.assertIn("demo", body[field].lower())

    async def test_network_error_returns_false(self) -> None:
        client = _RecordingClient(raises=httpx.ConnectError("DNS"))
        self.assertFalse(await self._send(client))


if __name__ == "__main__":
    unittest.main()
