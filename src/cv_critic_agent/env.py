from __future__ import annotations

from pathlib import Path


def load_env(root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(root / ".env.local", override=False)
    load_dotenv(root / ".env", override=False)
