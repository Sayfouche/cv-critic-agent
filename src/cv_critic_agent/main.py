from __future__ import annotations

import argparse
from pathlib import Path

from cv_critic_agent.crew import CVCriticCrew
from cv_critic_agent.env import load_env
from cv_critic_agent.paths import project_root


def run(mock: bool = False, root: Path | None = None) -> Path:
    """Official CrewAI-native entrypoint surface."""
    resolved_root = root or project_root()
    load_env(resolved_root)
    return CVCriticCrew(root=resolved_root, mock=mock).kickoff()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the official CV Critic Agent workflow.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM output.")
    parser.add_argument("--root", type=Path, default=None, help="Project root override for tests.")
    args = parser.parse_args()

    run_dir = run(mock=args.mock, root=args.root)
    print(f"[cv-critic-agent] reports written to {run_dir}")
    print("[cv-critic-agent] latest updated at reports/latest/")


if __name__ == "__main__":
    main()
