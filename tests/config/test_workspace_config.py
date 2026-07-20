"""Tests workspace configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import coercion, loader, schema
from agent_maintainer.core.config import MaintainerConfig


def test_default_config_has_no_workspaces() -> None:
    """Single-repository behavior stays unchanged without workspace config."""
    loaded = MaintainerConfig()

    assert loaded.workspaces == ()
    assert loaded.source_roots == ("src",)
    assert loaded.test_roots == ("tests",)
    assert loaded.coverage_source == ("src",)


def test_workspace_config_loads_named_tables(tmp_path: Path) -> None:
    """Workspace tables load without changing top-level roots."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
        [tool.agent_maintainer]
        source_roots = ["shared/src"]
        test_roots = ["shared/tests"]

        [tool.agent_maintainer.workspaces.worker]
        source_roots = ["services/worker/src"]
        test_roots = ["services/worker/tests"]
        coverage_source = ["services/worker/src"]

        [tool.agent_maintainer.workspaces.api]
        source_roots = ["services/api/src"]
        test_roots = ["services/api/tests"]
        package_paths = ["services/api/src"]
        coverage_source = ["services/api/src"]
        typescript_lint_command = ["pnpm", "--filter", "api", "lint"]
        typescript_typecheck_command = ["pnpm", "--filter", "api", "typecheck"]
        typescript_test_command = ["pnpm", "--filter", "api", "test"]
        typescript_knip_command = ["pnpm", "--filter", "api", "exec", "knip", "--reporter", "json"]
        typescript_dependency_cruiser_command = [
          "pnpm", "--filter", "api", "exec", "depcruise",
          "--output-type", "json", "src",
        ]
        typescript_package_manager_audit_manager = "pnpm"
        typescript_package_manager_audit_command = ["pnpm", "audit", "--json"]
        """,
        encoding="utf-8",
    )

    loaded = loader.apply_pyproject(
        MaintainerConfig(),
        loader.read_pyproject(pyproject),
    )

    assert loaded.source_roots == ("shared/src",)
    assert loaded.test_roots == ("shared/tests",)
    assert loaded.workspaces == (
        schema.WorkspaceConfig(
            name="api",
            source_roots=("services/api/src",),
            test_roots=("services/api/tests",),
            package_paths=("services/api/src",),
            coverage_source=("services/api/src",),
            typescript_lint_command=("pnpm", "--filter", "api", "lint"),
            typescript_typecheck_command=("pnpm", "--filter", "api", "typecheck"),
            typescript_test_command=("pnpm", "--filter", "api", "test"),
            typescript_knip_command=(
                "pnpm",
                "--filter",
                "api",
                "exec",
                "knip",
                "--reporter",
                "json",
            ),
            typescript_dependency_cruiser_command=(
                "pnpm",
                "--filter",
                "api",
                "exec",
                "depcruise",
                "--output-type",
                "json",
                "src",
            ),
            typescript_package_manager_audit_manager="pnpm",
            typescript_package_manager_audit_command=("pnpm", "audit", "--json"),
        ),
        schema.WorkspaceConfig(
            name="worker",
            source_roots=("services/worker/src",),
            test_roots=("services/worker/tests",),
            coverage_source=("services/worker/src",),
        ),
    )


def test_coerce_updates_reads_workspace_tables() -> None:
    """Top-level config coercion preserves nested workspace tables."""
    updates = coercion.coerce_updates(
        {
            "workspaces": {
                "api": {
                    "source_roots": ["services/api/src"],
                    "test_roots": ["services/api/tests"],
                    "typescript_lint_command": ["pnpm", "--filter", "api", "lint"],
                    "typescript_knip_command": [
                        "pnpm",
                        "--filter",
                        "api",
                        "exec",
                        "knip",
                        "--reporter",
                        "json",
                    ],
                    "typescript_dependency_cruiser_command": [
                        "pnpm",
                        "--filter",
                        "api",
                        "exec",
                        "depcruise",
                        "--output-type",
                        "json",
                        "src",
                    ],
                    "typescript_package_manager_audit_manager": "npm",
                    "typescript_package_manager_audit_command": [
                        "npm",
                        "audit",
                        "--json",
                    ],
                },
            },
        }
    )

    assert updates["workspaces"] == (
        schema.WorkspaceConfig(
            name="api",
            source_roots=("services/api/src",),
            test_roots=("services/api/tests",),
            typescript_lint_command=("pnpm", "--filter", "api", "lint"),
            typescript_knip_command=(
                "pnpm",
                "--filter",
                "api",
                "exec",
                "knip",
                "--reporter",
                "json",
            ),
            typescript_dependency_cruiser_command=(
                "pnpm",
                "--filter",
                "api",
                "exec",
                "depcruise",
                "--output-type",
                "json",
                "src",
            ),
            typescript_package_manager_audit_manager="npm",
            typescript_package_manager_audit_command=("npm", "audit", "--json"),
        ),
    )
    with pytest.raises(TypeError, match=r"workspaces\.api\.source_roots"):
        coercion.coerce_updates({"workspaces": {"api": {"source_roots": 12}}})
    with pytest.raises(TypeError, match=r"^workspaces\.api must be a table$"):
        coercion.coerce_workspace("api", [])
    with pytest.raises(TypeError, match=r"^workspaces must be a table$"):
        coercion.coerce_workspaces([])


def test_invalid_workspace_config_raises_clear_errors() -> None:
    """Invalid workspace tables fail with field-specific messages."""
    with pytest.raises(TypeError, match="workspaces must be a table"):
        coercion.coerce_workspaces(["api"])

    with pytest.raises(TypeError, match=r"workspaces\.api must be a table"):
        coercion.coerce_workspaces({"api": []})

    with pytest.raises(TypeError, match=r"workspaces\.api\.source_roots"):
        coercion.coerce_workspaces({"api": {"source_roots": 12}})
