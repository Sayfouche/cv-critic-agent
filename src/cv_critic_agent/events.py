"""Lifecycle events emitted during a CV Critic run.

The same event bus feeds the CLI rich UI (Phase 1), the FastAPI SSE stream
(Phase 2) and the React graph UI (Phase 3). Each subscriber decides how to
render the events.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

EventType = Literal[
    "run_started",
    "sources_loaded",
    "agent_started",
    "agent_token",
    "agent_completed",
    "file_written",
    "run_completed",
    "run_failed",
]


@dataclass
class Event:
    type: EventType
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Agent identifiers — kept stable across CLI, API and UI consumers.
AGENT_GLOBAL = "global_critic"
AGENT_CV = "printable_cv_critic"
AGENT_STRATEGY = "strategy_agent"

AGENT_LABELS: dict[str, str] = {
    AGENT_GLOBAL: "Global Critic",
    AGENT_CV: "Printable CV Critic",
    AGENT_STRATEGY: "Strategy Agent",
}

# Static graph topology — UI uses this to render the dependency graph before
# the run starts, then animates state per agent_started / agent_completed.
AGENT_GRAPH: list[dict[str, Any]] = [
    {"id": AGENT_GLOBAL, "label": AGENT_LABELS[AGENT_GLOBAL], "depends_on": []},
    {"id": AGENT_CV, "label": AGENT_LABELS[AGENT_CV], "depends_on": []},
    {"id": AGENT_STRATEGY, "label": AGENT_LABELS[AGENT_STRATEGY], "depends_on": [AGENT_GLOBAL, AGENT_CV]},
]


class EventBus:
    """Tiny synchronous pub/sub. Subscribers are simple callables."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self._subscribers.append(handler)

    def emit(self, event_type: EventType, **payload: Any) -> Event:
        # Normalise Path values so subscribers see strings consistently.
        clean_payload: dict[str, Any] = {}
        for key, value in payload.items():
            clean_payload[key] = str(value) if isinstance(value, Path) else value
        event = Event(type=event_type, payload=clean_payload)
        for handler in self._subscribers:
            handler(event)
        return event
