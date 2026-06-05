from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def strip_markdown_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```markdown"):
        text = text.removeprefix("```markdown").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text.removesuffix("```").strip()
    return text


def timestamp(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def create_run_dir(root: Path, now: datetime | None = None) -> Path:
    run_dir = root / "reports" / timestamp(now)
    run_dir.mkdir(parents=True, exist_ok=True)
    (root / "reports" / "latest").mkdir(parents=True, exist_ok=True)
    return run_dir


def write_report(root: Path, run_dir: Path, slug: str, content: str) -> Path:
    text = strip_markdown_fence(content) + "\n"
    run_path = run_dir / f"{slug}.md"
    latest_path = root / "reports" / "latest" / f"{slug}.md"
    run_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    return run_path


def write_summary(root: Path, run_dir: Path, generated: list[dict[str, str]]) -> None:
    lines = [
        "# CV Critic Run Summary",
        "",
        f"Generated at: {run_dir.name}",
        "Official engine: CrewAI native",
        "",
        "## Reports",
        *[f"- {item['title']}: {Path(item['path']).name}" for item in generated],
        "",
    ]
    write_report(root, run_dir, "summary", "\n".join(lines))
