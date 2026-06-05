"""Rich-powered terminal UI driven by the event bus.

Subscribes to Events and renders:
- header panel with provider/model/run id
- sources table with sizes
- live agent status table with spinner + duration
- output report list as files are written
- final summary panel

Falls back to plain prints if `rich` is unavailable.
"""
from __future__ import annotations

import os
import time
from typing import Any

from cv_critic_agent.events import (
    AGENT_GRAPH,
    Event,
    EventBus,
)

try:
    from rich.box import ROUNDED
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover — guarded fallback
    RICH_AVAILABLE = False


class RichCliUI:
    """Subscribes to the event bus and renders a live terminal UI."""

    def __init__(self, console: Console | None = None) -> None:
        if not RICH_AVAILABLE:
            raise RuntimeError("`rich` is required for the CLI UI. Install with `pip install rich`.")
        self.console = console or Console()
        self.run_id: str = "—"
        self.provider: str = "—"
        self.model: str = "—"
        self.mock: bool = False
        self.sources: list[dict[str, Any]] = []
        self.outputs: list[dict[str, Any]] = []
        self.agents: dict[str, dict[str, Any]] = {
            node["id"]: {"label": node["label"], "status": "pending", "started_at": None, "duration_ms": None}
            for node in AGENT_GRAPH
        }
        self.failed: dict[str, Any] | None = None

    # ── Public surface ────────────────────────────────────────────────────────
    def attach(self, bus: EventBus) -> None:
        bus.subscribe(self.handle)

    def handle(self, event: Event) -> None:
        kind = event.type
        if kind == "run_started":
            self.run_id = event.payload.get("run_id", "—")
            self.provider = event.payload.get("provider", "—")
            self.model = event.payload.get("model", "—")
            self.mock = bool(event.payload.get("mock", False))
        elif kind == "sources_loaded":
            self.sources = event.payload.get("sources", [])
        elif kind == "agent_started":
            agent = event.payload.get("agent")
            if agent in self.agents:
                self.agents[agent]["status"] = "running"
                self.agents[agent]["started_at"] = time.monotonic()
        elif kind == "agent_completed":
            agent = event.payload.get("agent")
            if agent in self.agents:
                self.agents[agent]["status"] = "done"
                started = self.agents[agent].get("started_at")
                if started is not None:
                    self.agents[agent]["duration_ms"] = int((time.monotonic() - started) * 1000)
        elif kind == "file_written":
            self.outputs.append({
                "slug": event.payload.get("slug"),
                "path": event.payload.get("path"),
                "size": event.payload.get("size"),
            })
        elif kind == "run_failed":
            self.failed = {
                "agent": event.payload.get("agent"),
                "message": event.payload.get("message"),
            }

    # ── Rendering ─────────────────────────────────────────────────────────────
    def render(self) -> Group:
        return Group(self._header(), self._sources_panel(), self._agents_panel(), self._outputs_panel())

    def live(self) -> Live:
        return Live(self.render(), console=self.console, refresh_per_second=8, transient=False)

    def _header(self) -> Panel:
        mode = "[bold yellow]MOCK[/bold yellow]" if self.mock else "[bold green]REAL[/bold green]"
        text = Text.from_markup(
            f"[bold]Provider:[/bold] {self.provider}    "
            f"[bold]Model:[/bold] {self.model}    "
            f"[bold]Mode:[/bold] {mode}\n"
            f"[dim]Run id:[/dim] {self.run_id}"
        )
        return Panel(text, title="🤖 CV Critic Agent", border_style="cyan", box=ROUNDED)

    def _sources_panel(self) -> Panel:
        if not self.sources:
            body = Text("(waiting for sources...)", style="dim")
        else:
            table = Table(box=None, show_header=True, header_style="bold cyan", expand=True)
            table.add_column("File", style="white")
            table.add_column("Size", justify="right", style="dim")
            for source in self.sources:
                size_kb = source.get("size", 0) / 1024
                table.add_row(source.get("path", "?"), f"{size_kb:5.1f} KB")
            body = table
        return Panel(body, title=f"📂 Sources ({len(self.sources)})", border_style="blue", box=ROUNDED)

    def _agents_panel(self) -> Panel:
        table = Table(box=None, show_header=True, header_style="bold cyan", expand=True)
        table.add_column(" ", width=3)
        table.add_column("Agent", style="white")
        table.add_column("Status", justify="right")
        for _agent_id, state in self.agents.items():
            icon, color = _status_decoration(state["status"])
            duration = ""
            if state["status"] == "running" and state["started_at"]:
                elapsed = time.monotonic() - state["started_at"]
                duration = f"  [dim]{elapsed:4.1f}s[/dim]"
            elif state["status"] == "done" and state["duration_ms"] is not None:
                duration = f"  [dim]{state['duration_ms'] / 1000:4.1f}s[/dim]"
            table.add_row(icon, state["label"], Text.from_markup(f"[{color}]{state['status']}[/{color}]{duration}"))
        return Panel(table, title="🤖 Agents", border_style="magenta", box=ROUNDED)

    def _outputs_panel(self) -> Panel:
        if not self.outputs:
            body = Text("(no reports yet)", style="dim")
        else:
            table = Table(box=None, show_header=True, header_style="bold cyan", expand=True)
            table.add_column("Report", style="white")
            table.add_column("Path", style="dim")
            table.add_column("Size", justify="right", style="dim")
            for output in self.outputs:
                size_kb = (output.get("size") or 0) / 1024
                table.add_row(output.get("slug", "?"), output.get("path", "?"), f"{size_kb:5.1f} KB")
            body = table
        return Panel(body, title=f"📝 Reports ({len(self.outputs)})", border_style="green", box=ROUNDED)


def _status_decoration(status: str) -> tuple[str, str]:
    if status == "running":
        return ("⏳", "yellow")
    if status == "done":
        return ("✓", "green")
    if status == "failed":
        return ("✗", "red")
    return ("⏸", "dim")


def is_rich_available() -> bool:
    """Check if rich is installed and we should use the rich UI."""
    return RICH_AVAILABLE and os.environ.get("CV_CRITIC_NO_RICH") != "1"
