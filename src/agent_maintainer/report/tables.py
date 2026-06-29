"""Render report tables and local artifact links."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Any


def check_table(
    checks: list[dict[str, Any]],
    log_dir: Path,
    output_dir: Path,
    *,
    include_expansion: bool,
) -> str:
    """Render a check table with links relative to the report output."""
    rows = "".join(_check_row(check, log_dir, output_dir, include_expansion) for check in checks)
    return (
        "<table><thead><tr><th>Check</th><th>Status</th><th>Log</th>"
        "<th>Artifacts</th><th>Expansion</th></tr></thead><tbody>"
        f"{rows}</tbody></table>"
    )


def list_items(items: list[str], *, already_html: bool = False) -> str:
    """Render a compact unordered list."""
    if not items:
        return ""
    rendered = "".join(_list_item(item, already_html=already_html) for item in items)
    return f"<ul>{rendered}</ul>"


def string_items(values: object) -> list[str]:
    """Coerce a JSON-ish value into a list of strings."""
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        item = text(value, "")
        if item:
            items.append(item)
    return items


def text(value: object, default: str) -> str:
    """Coerce a scalar report value into display text."""
    if isinstance(value, str | int | float | bool):
        return str(value)
    return default


def local_href(target: Path, output_dir: Path) -> str:
    """Return a local link target relative to the report output directory."""
    href = os.path.relpath(target, output_dir)
    return escape(Path(href).as_posix(), quote=True)


def _check_row(
    check: dict[str, Any],
    log_dir: Path,
    output_dir: Path,
    include_expansion: bool,
) -> str:
    name = text(check.get("name"), "unknown")
    status = text(check.get("status"), "unknown")
    log_cell = _linked_path(check.get("log_path"), log_dir, output_dir)
    artifact_cell = _linked_paths(check.get("artifacts"), log_dir, output_dir)
    expansion_cell = ""
    if include_expansion:
        expansion_cell = list_items(string_items(check.get("expansion_commands")))
    return (
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f'<td class="status-{escape(status)}">{escape(status)}</td>'
        f"<td>{log_cell}</td>"
        f"<td>{artifact_cell}</td>"
        f"<td>{expansion_cell}</td>"
        "</tr>"
    )


def _linked_path(value: object, log_dir: Path, output_dir: Path) -> str:
    path_text = text(value, "")
    if not path_text:
        return ""
    target = _repo_relative_target(path_text, log_dir)
    return f'<a href="{local_href(target, output_dir)}">{escape(path_text)}</a>'


def _linked_paths(values: object, log_dir: Path, output_dir: Path) -> str:
    paths = string_items(values)
    if not paths:
        return ""
    links = [
        _artifact_link(path_text, log_dir=log_dir, output_dir=output_dir) for path_text in paths
    ]
    return list_items(links, already_html=True)


def _artifact_link(path_text: str, *, log_dir: Path, output_dir: Path) -> str:
    target = _repo_relative_target(path_text, log_dir)
    return f'<a href="{local_href(target, output_dir)}">{escape(path_text)}</a>'


def _repo_relative_target(path_text: str, log_dir: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return log_dir.parent / path


def _list_item(item: str, *, already_html: bool) -> str:
    body = item if already_html else escape(item)
    return f"<li>{body}</li>"
