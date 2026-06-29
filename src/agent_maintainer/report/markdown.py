"""Helpers for extracting report sections from markdown artifacts."""

from __future__ import annotations


def summary_markdown_section(markdown: str, heading: str) -> str:
    """Return body text below a second-level heading."""
    lines = markdown.splitlines()
    start = _heading_index(lines, heading)
    if start is None:
        return ""
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    body_start = start + 1
    return "\n".join(lines[body_start:end]).strip()


def _heading_index(lines: list[str], heading: str) -> int | None:
    expected = f"## {heading}"
    for index, line in enumerate(lines):
        if line.strip() == expected:
            return index
    return None
