"""Regression tests for extracted internal package dependencies."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackageBoundary:
    """One extracted package dependency boundary."""

    package: str
    forbidden_top_level_imports: frozenset[str]


BOUNDARIES = (
    PackageBoundary(
        "agent_repair_facts",
        frozenset(
            {
                "agent_context",
                "agent_maintainer",
                "agent_run_artifacts",
                "archguard",
                "docsync",
            }
        ),
    ),
    PackageBoundary(
        "agent_context",
        frozenset(
            {
                "agent_client_hooks",
                "agent_maintainer",
                "agent_run_artifacts",
                "archguard",
                "docsync",
            }
        ),
    ),
    PackageBoundary(
        "agent_run_artifacts",
        frozenset(
            {
                "agent_client_hooks",
                "agent_maintainer",
                "archguard",
                "docsync",
            }
        ),
    ),
    PackageBoundary(
        "agent_client_hooks",
        frozenset(
            {
                "agent_context",
                "agent_maintainer",
                "agent_repair_facts",
                "agent_run_artifacts",
                "archguard",
                "docsync",
            }
        ),
    ),
    PackageBoundary(
        "docsync",
        frozenset(
            {
                "agent_maintainer",
                "archguard",
            }
        ),
    ),
)


def test_extracted_packages_do_not_import_forbidden_product_packages() -> None:
    """Extracted packages keep their documented dependency direction."""

    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []

    for boundary in BOUNDARIES:
        package_root = repo_root / "src" / boundary.package
        for source_path in sorted(package_root.rglob("*.py")):
            violations.extend(
                import_violations(
                    repo_root=repo_root,
                    source_path=source_path,
                    boundary=boundary,
                )
            )

    assert violations == []


def import_violations(
    *,
    repo_root: Path,
    source_path: Path,
    boundary: PackageBoundary,
) -> list[str]:
    """Return forbidden imports found in one source file."""

    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    violations: list[str] = []
    for node in ast.walk(tree):
        imported = imported_module(node)
        if imported is None:
            continue
        top_level = imported.partition(".")[0]
        if top_level in boundary.forbidden_top_level_imports:
            relative_path = source_path.relative_to(repo_root)
            violations.append(f"{relative_path} imports forbidden package {imported}")
    return violations


def imported_module(node: ast.AST) -> str | None:
    """Return module imported by an import node."""

    if isinstance(node, ast.Import):
        return node.names[0].name
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return node.module
    return None
