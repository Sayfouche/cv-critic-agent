"""Mistral-specific helpers — message cleaning and response extraction.

CrewAI's LiteLLM bridge forwards internal cache fields (`cache_breakpoint`) that
the Mistral API rejects. This module keeps the cleanup logic isolated so the
provider class in `llm.py` stays focused on configuration.
"""
from __future__ import annotations

from typing import Any


def extract_mistral_content(response: object) -> str:
    """Extract plain text from a Mistral chat completion response."""
    choice = response.choices[0]
    content = choice.message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip()
    return str(content).strip()


def load_mistral_client_class() -> type:
    """Locate the Mistral client class across SDK versions."""
    try:
        from mistralai.client import Mistral

        return Mistral
    except ImportError:
        try:
            from mistralai import Mistral

            return Mistral
        except ImportError as exc:
            raise RuntimeError("Install mistralai or run with --mock.") from exc


def _plain_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                text = getattr(item, "text", None) or getattr(item, "content", None)
                if text:
                    parts.append(str(text))
        return "\n".join(parts)
    return str(content)


def clean_mistral_messages(messages: str | list[dict[str, Any]]) -> list[dict[str, str]]:
    """Strip CrewAI-internal fields and normalize content shape for Mistral."""
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]

    cleaned: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        if role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        cleaned.append({"role": role, "content": _plain_text_content(message.get("content", ""))})
    return cleaned
