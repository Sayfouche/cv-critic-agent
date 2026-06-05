from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from cv_critic_agent.events import (
    AGENT_CV,
    AGENT_GLOBAL,
    AGENT_STRATEGY,
    EventBus,
)
from cv_critic_agent.llm import TextLLM
from cv_critic_agent.prompts import build_critic_prompt, build_strategy_prompt
from cv_critic_agent.reports import create_run_dir, write_report, write_summary
from cv_critic_agent.sources import REPORT_SPECS

# Map ReportSpec.slug -> agent id used by the event bus / UI.
SPEC_TO_AGENT = {"global": AGENT_GLOBAL, "printable-cv": AGENT_CV}


def run_shared_workflow(
    root: Path,
    llm: TextLLM,
    now: datetime | None = None,
    bus: EventBus | None = None,
) -> Path:
    bus = bus or EventBus()
    run_dir = create_run_dir(root, now)
    run_date = (now.date() if now else date.today())

    # Announce sources up front so the UI/graph can show them as inputs.
    all_source_files = sorted({path for spec in REPORT_SPECS for path in spec.source_files})
    sources_payload = []
    for relative_path in all_source_files:
        absolute = root / relative_path
        sources_payload.append({
            "path": relative_path,
            "size": absolute.stat().st_size if absolute.exists() else 0,
            "exists": absolute.exists(),
        })
    bus.emit("sources_loaded", sources=sources_payload, run_dir=run_dir)

    report_contents: dict[str, str] = {}
    generated: list[dict[str, str]] = []

    for spec in REPORT_SPECS:
        agent_id = SPEC_TO_AGENT.get(spec.slug, spec.slug)
        bus.emit("agent_started", agent=agent_id, slug=spec.slug)
        prompt = build_critic_prompt(spec, root, run_date)
        content = llm.complete(prompt)
        path = write_report(root, run_dir, spec.slug, content)
        report_contents[spec.slug] = content
        generated.append({"title": spec.title, "path": str(path)})
        bus.emit("agent_completed", agent=agent_id, slug=spec.slug)
        bus.emit("file_written", slug=spec.slug, path=path, size=path.stat().st_size)

    bus.emit("agent_started", agent=AGENT_STRATEGY, slug="strategy")
    strategy = llm.complete(build_strategy_prompt(root, report_contents))
    strategy_path = write_report(root, run_dir, "strategy", strategy)
    generated.append({"title": "Rapport strategie et plan d'action", "path": str(strategy_path)})
    bus.emit("agent_completed", agent=AGENT_STRATEGY, slug="strategy")
    bus.emit("file_written", slug="strategy", path=strategy_path, size=strategy_path.stat().st_size)

    write_summary(root, run_dir, generated)
    bus.emit("file_written", slug="summary", path=run_dir / "summary.md", size=(run_dir / "summary.md").stat().st_size)
    return run_dir
