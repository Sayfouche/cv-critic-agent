#!/usr/bin/env python3
"""Sync the `sources/` directory from a cv-portfolio checkout.

The CV Critic Agent runs against snapshots of the portfolio source files (data.ts,
chatbot-knowledge.ts, system-prompt.ts, tools.ts, cv-page.tsx, technical-sheet.md).
Those snapshots are versioned in this repo so the agent stays runnable in isolation.

This script refreshes them from a local cv-portfolio checkout. It is intentionally
explicit (no symlinks, no git submodule) so each refresh becomes a reviewable diff.

Usage:
    python scripts/sync_sources.py /path/to/cv-portfolio
    python scripts/sync_sources.py /path/to/cv-portfolio --check    # exit 1 if drift
    CV_PORTFOLIO_ROOT=/path/to/cv-portfolio python scripts/sync_sources.py
"""
from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

# Mapping: portfolio_relative_path -> cv-critic-agent target path under sources/
SOURCE_MAP: dict[str, str] = {
    "src/lib/data.ts": "data.ts",
    "src/lib/chatbot-knowledge.ts": "chatbot-knowledge.ts",
    "src/lib/system-prompt.ts": "system-prompt.ts",
    "src/lib/tools.ts": "tools.ts",
    "src/app/cv/page.tsx": "cv-page.tsx",
    "public/technical-sheets/saif-ia-technical-sheet.md": "saif-ia-technical-sheet.md",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sync(portfolio_root: Path, check_only: bool = False) -> int:
    if not portfolio_root.exists():
        print(f"[sync-sources] portfolio path does not exist: {portfolio_root}", file=sys.stderr)
        return 2

    target_dir = repo_root() / "sources"
    target_dir.mkdir(parents=True, exist_ok=True)

    drift = 0
    for portfolio_rel, target_name in SOURCE_MAP.items():
        source = portfolio_root / portfolio_rel
        target = target_dir / target_name

        if not source.exists():
            print(f"[sync-sources] MISSING in portfolio: {portfolio_rel}", file=sys.stderr)
            drift += 1
            continue

        if target.exists() and filecmp.cmp(source, target, shallow=False):
            print(f"[sync-sources] OK     {target_name}")
            continue

        if check_only:
            print(f"[sync-sources] DRIFT  {target_name}")
            drift += 1
            continue

        shutil.copyfile(source, target)
        print(f"[sync-sources] UPDATE {target_name} <- {portfolio_rel}")

    if check_only and drift:
        print(f"[sync-sources] {drift} file(s) drifted from portfolio. Run without --check to sync.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "portfolio_root",
        nargs="?",
        type=Path,
        default=Path(os.environ.get("CV_PORTFOLIO_ROOT", "")),
        help="Path to the cv-portfolio checkout (defaults to $CV_PORTFOLIO_ROOT).",
    )
    parser.add_argument("--check", action="store_true", help="Exit 1 if files drift; do not write.")
    args = parser.parse_args()

    if not args.portfolio_root or args.portfolio_root == Path(""):
        parser.error("Provide a path argument or set CV_PORTFOLIO_ROOT.")

    return sync(args.portfolio_root.resolve(), check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
