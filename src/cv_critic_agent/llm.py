from __future__ import annotations

import os
from typing import Any, Protocol

from cv_critic_agent.mistral_utils import (
    clean_mistral_messages,
    extract_mistral_content,
    load_mistral_client_class,
)

__all__ = [
    "DEFAULT_PROVIDER",
    "DEFAULT_MISTRAL_MODEL",
    "DEFAULT_ANTHROPIC_MODEL",
    "DEFAULT_MOCK_RESPONSES",
    "DEFAULT_MOCK_FALLBACK",
    "TextLLM",
    "MockLLM",
    "MistralTextLLM",
    "MistralCrewLLM",
    "AnthropicTextLLM",
    "create_text_llm",
    "clean_mistral_messages",
]

DEFAULT_PROVIDER = "mistral"
DEFAULT_MISTRAL_MODEL = "mistral-medium-latest"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


class TextLLM(Protocol):
    def complete(self, prompt: str) -> str:
        ...


DEFAULT_MOCK_RESPONSES: dict[str, str] = {
    # Order matters — first match wins, strategy must be tested before critic headings
    # appear in the strategy prompt template.
    "Tu es CV Strategy Agent": "# Strategie CV\n\n## Synthese executive\nMock strategy output.",
    "# Rapport critique global": "# Rapport critique global\n\n## Verdict court\nMock global critic output.",
    "# Rapport critique CV imprimable": "# Rapport critique CV imprimable\n\n## Verdict court\nMock printable CV critic output.",
}

DEFAULT_MOCK_FALLBACK = "# Strategie CV\n\n## Synthese executive\nMock strategy output."


class MockLLM:
    """Deterministic LLM stub for tests and `--mock` runs.

    By default uses heuristic markers to pick a canned response. Tests can
    pass `responses=` to inject custom outputs and verify pipeline behaviour
    without depending on prompt internals.
    """

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        fallback: str = DEFAULT_MOCK_FALLBACK,
    ) -> None:
        self._responses = responses if responses is not None else DEFAULT_MOCK_RESPONSES
        self._fallback = fallback

    def complete(self, prompt: str) -> str:
        for marker, response in self._responses.items():
            if marker in prompt:
                return response
        return self._fallback


def create_text_llm() -> TextLLM:
    provider = os.getenv("CV_CRITIC_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider == "mistral":
        return MistralTextLLM()
    if provider == "anthropic":
        return AnthropicTextLLM()
    raise RuntimeError(f"Unsupported CV_CRITIC_PROVIDER: {provider}")


class MistralTextLLM:
    def __init__(self) -> None:
        Mistral = load_mistral_client_class()

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
        return extract_mistral_content(response)


try:
    from crewai.llms.base_llm import BaseLLM
except ImportError:
    BaseLLM = None  # type: ignore[assignment]


if BaseLLM is not None:

    class MistralCrewLLM(BaseLLM):
        """CrewAI-native LLM adapter that calls Mistral directly.

        CrewAI's LiteLLM path currently forwards internal cache fields that the
        Mistral API rejects. This adapter keeps the CrewAI Agent/Task/Crew model
        while sending only Mistral-supported message fields.
        """

        provider: str = "mistral"

        def __init__(
            self,
            model: str | None = None,
            api_key: str | None = None,
            temperature: float = 0.2,
            max_tokens: int = 5000,
        ) -> None:
            resolved_api_key = api_key or os.getenv("MISTRAL_API_KEY")
            if not resolved_api_key:
                raise RuntimeError("MISTRAL_API_KEY is required unless --mock is used.")

            super().__init__(
                model=model or os.getenv("CV_CRITIC_MODEL", DEFAULT_MISTRAL_MODEL),
                api_key=resolved_api_key,
                temperature=temperature,
                provider="mistral",
                additional_params={"max_tokens": max_tokens},
            )
            Mistral = load_mistral_client_class()
            object.__setattr__(self, "_client", Mistral(api_key=resolved_api_key))

        def call(
            self,
            messages: str | list[dict[str, Any]],
            tools: list[dict[str, Any]] | None = None,
            callbacks: list[Any] | None = None,
            available_functions: dict[str, Any] | None = None,
            from_task: Any | None = None,
            from_agent: Any | None = None,
            response_model: type[Any] | None = None,
        ) -> str:
            if tools:
                raise RuntimeError("MistralCrewLLM does not support CrewAI tool calls for this agent.")
            if response_model:
                raise RuntimeError("MistralCrewLLM does not support response_model for this agent.")

            response = self._client.chat.complete(
                model=self.model,
                messages=clean_mistral_messages(messages),
                temperature=self.temperature,
                max_tokens=int(self.additional_params.get("max_tokens", 5000)),
            )
            return self._apply_stop_words(extract_mistral_content(response))

else:
    MistralCrewLLM = None  # type: ignore[assignment]


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
