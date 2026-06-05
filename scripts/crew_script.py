#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cv_critic_agent.llm import AnthropicTextLLM, MockLLM
from cv_critic_agent.paths import project_root
from cv_critic_agent.workflow import run_shared_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Migration-step CrewAI script workflow.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM output.")
    parser.add_argument("--root", type=Path, default=None, help="Project root override for tests.")
    args = parser.parse_args()

    llm = MockLLM() if args.mock else AnthropicTextLLM()
    run_dir = run_shared_workflow(args.root or project_root(), llm)
    print(f"[cv-critic-script] reports written to {run_dir}")


if __name__ == "__main__":
    main()
