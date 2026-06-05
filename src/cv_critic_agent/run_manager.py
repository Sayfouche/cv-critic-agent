"""Concurrent run manager.

Spawns the workflow on a worker thread, fans out the sync `EventBus` to one
queue per SSE subscriber, and keeps the full event log for polling/replay.

This is an in-memory implementation — fine for a single-instance deployment
(local CLI, Fly.io VM, single Vercel function). To horizontal-scale, swap the
per-subscriber queue for Redis pub/sub or NATS.
"""
from __future__ import annotations

import os
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from cv_critic_agent.crew import CVCriticCrew
from cv_critic_agent.env import load_env
from cv_critic_agent.events import Event, EventBus
from cv_critic_agent.llm import DEFAULT_MISTRAL_MODEL
from cv_critic_agent.paths import project_root

# Sentinel to signal the producer side is done.
_SENTINEL: dict[str, Any] = {"__sentinel__": True}


@dataclass
class RunState:
    run_id: str
    mock: bool
    provider: str
    model: str
    started_at: float = field(default_factory=time.monotonic)
    status: str = "running"  # running | done | failed
    events: list[dict[str, Any]] = field(default_factory=list)
    subscribers: list[Queue] = field(default_factory=list)
    run_dir: str | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)


class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._lock = threading.Lock()

    def create_run(self, mock: bool = True, root: Path | None = None) -> RunState:
        run_id = uuid.uuid4().hex[:12]
        provider = os.environ.get("CV_CRITIC_PROVIDER", "mistral")
        model = os.environ.get("CV_CRITIC_MODEL", DEFAULT_MISTRAL_MODEL)
        state = RunState(run_id=run_id, mock=mock, provider=provider, model=model)
        with self._lock:
            self._runs[run_id] = state

        thread = threading.Thread(target=self._execute, args=(state, root), daemon=True)
        thread.start()
        return state

    def get(self, run_id: str) -> RunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "run_id": s.run_id,
                    "status": s.status,
                    "mock": s.mock,
                    "provider": s.provider,
                    "model": s.model,
                    "started_at": s.started_at,
                }
                for s in self._runs.values()
            ]

    # ── Worker thread ─────────────────────────────────────────────────────────
    def _execute(self, state: RunState, root: Path | None) -> None:
        bus = EventBus()
        bus.subscribe(lambda event: self._record_event(state, event))

        try:
            resolved_root = root or project_root()
            load_env(resolved_root)
            bus.emit(
                "run_started",
                run_id=state.run_id,
                provider=state.provider,
                model=state.model,
                mock=state.mock,
            )

            run_dir = CVCriticCrew(root=resolved_root, mock=state.mock, bus=bus).kickoff()
            state.run_dir = str(run_dir)
            bus.emit("run_completed", run_dir=str(run_dir), run_id=state.run_id)
            state.status = "done"
        except Exception as exc:  # pragma: no cover — surfaced via events
            state.error = str(exc)
            state.status = "failed"
            bus.emit(
                "run_failed",
                run_id=state.run_id,
                message=str(exc),
                traceback=traceback.format_exc(),
            )
        finally:
            # Close all subscriber queues.
            with state._lock:
                for queue in state.subscribers:
                    queue.put(_SENTINEL)

    def _record_event(self, state: RunState, event: Event) -> None:
        payload = event.to_dict()
        with state._lock:
            state.events.append(payload)
            for queue in state.subscribers:
                queue.put(payload)

    # ── SSE subscriber API ────────────────────────────────────────────────────
    def subscribe(self, run_id: str) -> Queue | None:
        """Create a new queue that receives every future event.

        Replay of past events is the caller's job (read `state.events`).
        """
        state = self.get(run_id)
        if state is None:
            return None
        queue: Queue = Queue()
        with state._lock:
            state.subscribers.append(queue)
            # If the run is already over, immediately close.
            if state.status != "running":
                queue.put(_SENTINEL)
        return queue

    @staticmethod
    def is_sentinel(item: Any) -> bool:
        return isinstance(item, dict) and item.get("__sentinel__") is True

    @staticmethod
    def drain(queue: Queue, timeout: float = 0.5):
        try:
            return queue.get(timeout=timeout)
        except Empty:
            return None
