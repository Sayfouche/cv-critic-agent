from __future__ import annotations

import os
from typing import Protocol


class TextLLM(Protocol):
    def complete(self, prompt: str) -> str:
        ...


class MockLLM:
    def complete(self, prompt: str) -> str:
        if "Tu es CV Strategy Agent" in prompt:
            return "# Strategie CV\n\n## Synthese executive\nMock strategy output."
        if "# Rapport critique global" in prompt:
            return "# Rapport critique global\n\n## Verdict court\nMock global critic output."
        if "# Rapport critique CV imprimable" in prompt:
            return "# Rapport critique CV imprimable\n\n## Verdict court\nMock printable CV critic output."
        return "# Strategie CV\n\n## Synthese executive\nMock strategy output."


class AnthropicTextLLM:
    def __init__(self) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("Install anthropic or run with --mock.") from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required unless --mock is used.")

        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv("CV_CRITIC_MODEL", "claude-haiku-4-5-20251001")

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 5000,
            "messages": [{"role": "user", "content": prompt}],
        }
        if "claude-opus-4" not in self.model:
            payload["temperature"] = 0.2

        message = self.client.messages.create(**payload)
        return "\n\n".join(block.text for block in message.content if block.type == "text").strip()
