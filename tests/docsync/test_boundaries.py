"""Tests for DocSync extraction boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORTS = ("agent_maintainer", "archguard")


def test_docsync_imports_no_project_internal_packages() -> None:
    """DocSync must remain extractable from this repository."""
    repo_root = Path(__file__).resolve().parents[2]
    source_root = repo_root / "src" / "docsync"
    violations: list[str] = []

    for path in sorted(source_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported = _imported_module(node)
            if imported is None:
                continue
            if imported.partition(".")[0] in FORBIDDEN_IMPORTS:
                violations.append(f"{path.relative_to(repo_root)} imports {imported}")

    assert violations == []


def _imported_module(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return node.module
    return None
