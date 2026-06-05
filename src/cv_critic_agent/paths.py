from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def reports_dir(root: Path) -> Path:
    return root / "reports"


def latest_dir(root: Path) -> Path:
    return reports_dir(root) / "latest"


def context_path(root: Path) -> Path:
    return root / "context.md"
