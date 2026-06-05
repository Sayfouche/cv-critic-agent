from __future__ import annotations

import os
from typing import Protocol

DEFAULT_PROVIDER = "mistral"
DEFAULT_MISTRAL_MODEL = "mistral-medium-latest"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


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


def create_text_llm() -> TextLLM:
    provider = os.getenv("CV_CRITIC_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider == "mistral":
        return MistralTextLLM()
    if provider == "anthropic":
        return AnthropicTextLLM()
    raise RuntimeError(f"Unsupported CV_CRITIC_PROVIDER: {provider}")


def _extract_mistral_content(response: object) -> str:
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


class MistralTextLLM:
    def __init__(self) -> None:
        try:
            from mistralai.client import Mistral
        except ImportError:
            try:
                from mistralai import Mistral
            except ImportError as exc:
                raise RuntimeError("Install mistralai or run with --mock.") from exc

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is required unless --mock is used.")

        self.client = Mistral(api_key=api_key)
        self.model = os.getenv("CV_CRITIC_MODEL", DEFAULT_MISTRAL_MODEL)

    def complete(self, prompt: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=5000,
        )
        return _extract_mistral_content(response)


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
        self.model = os.getenv("CV_CRITIC_MODEL", DEFAULT_ANTHROPIC_MODEL)

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
