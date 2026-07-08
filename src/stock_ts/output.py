from __future__ import annotations

from pathlib import Path


def write_optional_text(content: str, output: str | None) -> Path | None:
    if output is None:
        return None
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
