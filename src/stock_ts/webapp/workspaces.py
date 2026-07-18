from __future__ import annotations

from .composition import group_sections_by_workspace
from .shell import render_workspace_shell


def build_workspace_sections(
    section_map: dict[str, str],
    *,
    holdings_path: str = "",
) -> str:
    return render_workspace_shell(
        group_sections_by_workspace(section_map),
        holdings_path=holdings_path,
    )
