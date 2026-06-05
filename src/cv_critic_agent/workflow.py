from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from cv_critic_agent.llm import TextLLM
from cv_critic_agent.prompts import build_critic_prompt, build_strategy_prompt
from cv_critic_agent.reports import create_run_dir, write_report, write_summary
from cv_critic_agent.sources import REPORT_SPECS


def run_shared_workflow(root: Path, llm: TextLLM, now: datetime | None = None) -> Path:
    run_dir = create_run_dir(root, now)
    run_date = (now.date() if now else date.today())
    report_contents: dict[str, str] = {}
    generated: list[dict[str, str]] = []

    for spec in REPORT_SPECS:
        prompt = build_critic_prompt(spec, root, run_date)
        content = llm.complete(prompt)
        path = write_report(root, run_dir, spec.slug, content)
        report_contents[spec.slug] = content
        generated.append({"title": spec.title, "path": str(path)})

    strategy = llm.complete(build_strategy_prompt(root, report_contents))
    strategy_path = write_report(root, run_dir, "strategy", strategy)
    generated.append({"title": "Rapport strategie et plan d'action", "path": str(strategy_path)})

    write_summary(root, run_dir, generated)
    return run_dir
