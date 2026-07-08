from __future__ import annotations


def workspace_action(fragment: str) -> str:
    normalized = fragment if fragment.startswith("#") else f"#{fragment}"
    return f"/{normalized}"
