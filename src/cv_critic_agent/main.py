from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path

from cv_critic_agent.cli_ui import RichCliUI, is_rich_available
from cv_critic_agent.crew import CVCriticCrew
from cv_critic_agent.env import load_env
from cv_critic_agent.events import EventBus
from cv_critic_agent.llm import DEFAULT_MISTRAL_MODEL, MockLLM, create_text_llm
from cv_critic_agent.paths import project_root
from cv_critic_agent.workflow import run_shared_workflow


def run(mock: bool = False, root: Path | None = None, bus: EventBus | None = None) -> Path:
    """Official CrewAI-native entrypoint surface."""
    resolved_root = root or project_root()
    load_env(resolved_root)
    return CVCriticCrew(root=resolved_root, mock=mock, bus=bus).kickoff()


def _run_with_cli_ui(mock: bool, root: Path | None, plain: bool) -> Path:
    """Run the workflow with the rich CLI UI subscribed to events.

    Note: the rich UI only renders cleanly with the shared workflow path
    (`workflow.py`). The CrewAI native path swallows events inside the framework
    loop, so when not in mock and not in plain mode we still use the shared
    workflow for nice rendering. Pass --plain to force the raw CrewAI runner.
    """
    resolved_root = root or project_root()
    load_env(resolved_root)
    bus = EventBus()

    use_rich = is_rich_available() and not plain
    ui: RichCliUI | None = None
    if use_rich:
        ui = RichCliUI()
        ui.attach(bus)

    provider = os.environ.get("CV_CRITIC_PROVIDER", "mistral")
    model = os.environ.get("CV_CRITIC_MODEL", DEFAULT_MISTRAL_MODEL)
    run_id = uuid.uuid4().hex[:12]

    bus.emit("run_started", run_id=run_id, provider=provider, model=model, mock=mock)

    # For the rich CLI path we use the shared workflow so we get per-agent events.
    # CrewAI native still exists and works without --rich.
    llm = MockLLM() if mock else create_text_llm()

    if use_rich and ui is not None:
        with ui.live() as live:
            try:
                run_dir = run_shared_workflow(resolved_root, llm, bus=bus)
            except Exception as exc:
                bus.emit("run_failed", message=str(exc))
                live.update(ui.render())
                raise
            else:
                bus.emit("run_completed", run_dir=str(run_dir))
                live.update(ui.render())
            return run_dir

    # Fallback: plain mode, no rich
    run_dir = run_shared_workflow(resolved_root, llm, bus=bus)
    bus.emit("run_completed", run_dir=str(run_dir))
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the official CV Critic Agent workflow.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM output.")
    parser.add_argument("--root", type=Path, default=None, help="Project root override for tests.")
    parser.add_argument("--plain", action="store_true", help="Disable rich CLI UI (raw output).")
    parser.add_argument(
        "--crewai-native",
        action="store_true",
        help="Use the CrewAI Agent/Task/Crew path instead of the shared workflow.",
    )
    args = parser.parse_args()

    if args.crewai_native:
        # No rich UI for the framework-driven path — CrewAI owns the loop.
        run_dir = run(mock=args.mock, root=args.root)
    else:
        run_dir = _run_with_cli_ui(mock=args.mock, root=args.root, plain=args.plain)

    if args.plain or args.crewai_native:
        print(f"[cv-critic-agent] reports written to {run_dir}")
        print("[cv-critic-agent] latest updated at reports/latest/")


if __name__ == "__main__":
    main()
