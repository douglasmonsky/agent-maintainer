"""Tests experimental TypeScript catalog integration."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.config import loader, schema
from agent_maintainer.core import executor
from agent_maintainer.core.config import MaintainerConfig

DEPENDENCY_CRUISER_OUTPUT_LIMIT = 5_000_000


# docsync:evidence.start evidence.typescript.dependency_cruiser_config_tests
def test_typescript_checks_are_absent_by_default() -> None:
    """Default Python catalog behavior does not include TypeScript checks."""
    checks = maintainer_catalog.make_checks(
        MaintainerConfig(),
        "HEAD",
        "origin/main",
    )

    assert not [check for check in checks if check.name.startswith("typescript-")]


def test_typescript_checks_are_included_when_enabled() -> None:
    """Enabled TypeScript provider contributes configured checks."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=("npm", "run", "lint"),
        typescript_typecheck_command=("npm", "run", "typecheck"),
        typescript_test_command=("npm", "test"),
        typescript_knip_command=("pnpm", "exec", "knip", "--reporter", "json"),
        typescript_dependency_cruiser_command=(
            "pnpm",
            "exec",
            "depcruise",
            "--output-type",
            "json",
            "src",
        ),
    )

    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    by_name = {check.name: check for check in checks}

    assert by_name["typescript-lint"].command == ["npm", "run", "lint"]
    assert by_name["typescript-typecheck"].command == ["npm", "run", "typecheck"]
    assert by_name["typescript-test"].command == ["npm", "test"]
    assert by_name["typescript-knip"].command == [
        "pnpm",
        "exec",
        "knip",
        "--reporter",
        "json",
    ]
    assert by_name["typescript-knip"].profiles == frozenset(("full", "ci"))
    assert by_name["typescript-dependency-cruiser"].command == [
        "pnpm",
        "exec",
        "depcruise",
        "--output-type",
        "json",
        "src",
    ]
    assert by_name["typescript-dependency-cruiser"].profiles == frozenset(("full", "ci"))


def test_depcruise_large_output_reaches_summary(tmp_path: Path) -> None:
    """Configured checks preserve large valid cruise-result JSON."""

    script = tmp_path / "emit_depcruise.py"
    script.write_text(
        "import json\n"
        "payload = {"
        "'summary': {'violations': [{"
        "'from': 'src/source.ts', "
        "'to': 'src/target.ts', "
        "'type': 'dependency', "
        "'rule': {'name': 'big-json-rule', 'severity': 'warn'}"
        "}]}, "
        "'modules': [{'source': 'x' * 1_100_000}]"
        "}\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_dependency_cruiser_command=(sys.executable, str(script)),
    )
    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    check = next(item for item in checks if item.name == "typescript-dependency-cruiser")

    assert check.output_limit_chars == DEPENDENCY_CRUISER_OUTPUT_LIMIT
    assert check.report_success_output is True

    result = executor.run_check(
        check,
        tmp_path / "logs",
        max_lines=50,
        max_chars=5_000,
    )

    assert result.passed is True
    assert result.warning is True
    assert "big-json-rule" in result.output


def test_workspace_typescript_commands_emit_owned_checks() -> None:
    """Workspace TypeScript commands create explicit package-owned checks."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        workspaces=(
            schema.WorkspaceConfig(
                name="api",
                typescript_lint_command=("pnpm", "--filter", "api", "lint"),
                typescript_typecheck_command=(
                    "pnpm",
                    "--filter",
                    "api",
                    "typecheck",
                ),
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
            ),
        ),
    )

    checks = {
        check.name: check for check in maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    }

    assert checks["typescript-lint:api"].command == [
        "pnpm",
        "--filter",
        "api",
        "lint",
    ]
    assert checks["typescript-typecheck:api"].command == [
        "pnpm",
        "--filter",
        "api",
        "typecheck",
    ]
    assert "typescript-test:api" not in checks
    assert checks["typescript-knip:api"].command == [
        "pnpm",
        "--filter",
        "api",
        "exec",
        "knip",
        "--reporter",
        "json",
    ]
    assert checks["typescript-knip:api"].profiles == frozenset(("full", "ci"))
    assert checks["typescript-dependency-cruiser:api"].command == [
        "pnpm",
        "--filter",
        "api",
        "exec",
        "depcruise",
        "--output-type",
        "json",
        "src",
    ]
    assert checks["typescript-dependency-cruiser:api"].profiles == frozenset(("full", "ci"))


def test_typescript_fixture_config_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Minimal TypeScript-enabled repo config produces expected checks."""
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
enable_typescript = true
typescript_lint_command = ["npm", "run", "lint"]
typescript_typecheck_command = ["npm", "run", "typecheck"]
typescript_test_command = ["npm", "test"]
typescript_knip_command = ["pnpm", "exec", "knip", "--reporter", "json"]
typescript_dependency_cruiser_command = [
  "pnpm", "exec", "depcruise", "--output-type", "json", "src",
]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config = loader.load_config()
    checks = {
        check.name: check
        for check in maintainer_catalog.make_checks(
            config,
            "HEAD",
            "origin/main",
        )
    }

    assert checks["typescript-lint"].command == ["npm", "run", "lint"]
    assert checks["typescript-typecheck"].command == ["npm", "run", "typecheck"]
    assert checks["typescript-test"].command == ["npm", "test"]
    assert checks["typescript-knip"].command == [
        "pnpm",
        "exec",
        "knip",
        "--reporter",
        "json",
    ]
    assert checks["typescript-dependency-cruiser"].command == [
        "pnpm",
        "exec",
        "depcruise",
        "--output-type",
        "json",
        "src",
    ]


# docsync:evidence.end evidence.typescript.dependency_cruiser_config_tests
