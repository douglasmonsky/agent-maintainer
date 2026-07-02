"""Tests experimental TypeScript catalog integration."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.core.config import MaintainerConfig


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
    )

    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    by_name = {check.name: check for check in checks}

    assert by_name["typescript-lint"].command == ["npm", "run", "lint"]
    assert by_name["typescript-typecheck"].command == ["npm", "run", "typecheck"]
    assert by_name["typescript-test"].command == ["npm", "test"]
