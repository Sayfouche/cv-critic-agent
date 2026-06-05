#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cv_critic_agent.env import load_env
from cv_critic_agent.llm import MockLLM, create_text_llm
from cv_critic_agent.paths import project_root
from cv_critic_agent.workflow import run_shared_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Migration-step CrewAI script workflow.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM output.")
    parser.add_argument("--root", type=Path, default=None, help="Project root override for tests.")
    args = parser.parse_args()

    root = args.root or project_root()
    load_env(root)
    llm = MockLLM() if args.mock else create_text_llm()
    run_dir = run_shared_workflow(root, llm)
    print(f"[cv-critic-script] reports written to {run_dir}")


if __name__ == "__main__":
    main()
