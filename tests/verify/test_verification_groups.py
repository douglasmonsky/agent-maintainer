"""Tests for fail-closed verifier check grouping."""

from __future__ import annotations

import pytest

from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.core.config import load_config
from agent_maintainer.models import CI_ONLY_PROFILES, Check
from agent_maintainer.verify.groups import (
    GROUP_NAMES,
    VerificationGroupError,
    checks_for_group,
)


def check(name: str) -> Check:
    """Return a minimal CI check."""

    return Check(name, [name], CI_ONLY_PROFILES)


def test_group_selection_preserves_catalog_order() -> None:
    checks = [
        check("ruff"),
        check("pytest-coverage"),
        check("typescript-test:web"),
        check("diff-cover"),
    ]

    selected = checks_for_group(checks, "tests-and-coverage")

    assert GROUP_NAMES == ("tests-and-coverage", "static-and-policy")
    assert [item.name for item in selected] == [
        "pytest-coverage",
        "typescript-test:web",
        "diff-cover",
    ]


def test_static_group_receives_non_test_catalog_checks() -> None:
    checks = [check("ruff"), check("pytest-coverage"), check("typescript-typecheck:web")]

    selected = checks_for_group(checks, "static-and-policy")

    assert [item.name for item in selected] == ["ruff", "typescript-typecheck:web"]


def test_unknown_group_fails_closed() -> None:
    with pytest.raises(VerificationGroupError, match="unknown verification group"):
        checks_for_group([check("ruff")], "never-heard-of-it")


def test_duplicate_check_names_fail_closed() -> None:
    with pytest.raises(VerificationGroupError, match="duplicate check name: ruff"):
        checks_for_group([check("ruff"), check("ruff")], "static-and-policy")


def test_unassigned_catalog_check_fails_closed() -> None:
    with pytest.raises(VerificationGroupError, match="unassigned check: future-check"):
        checks_for_group([check("future-check")], "static-and-policy")


def test_current_ci_catalog_is_completely_partitioned() -> None:
    """Catalog evolution must update the explicit grouping contract."""

    configured = make_checks(load_config(), "HEAD", "origin/main")
    ci_checks = [item for item in configured if "ci" in item.profiles]

    grouped = [item for group in GROUP_NAMES for item in checks_for_group(ci_checks, group)]

    assert sorted(item.name for item in grouped) == sorted(item.name for item in ci_checks)
