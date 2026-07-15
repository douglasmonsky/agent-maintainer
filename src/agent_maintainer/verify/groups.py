"""Fail-closed grouping for independently runnable verifier checks."""

from __future__ import annotations

from collections.abc import Sequence

from agent_maintainer.models import Check
from agent_run_artifacts.verification_aggregate import REQUIRED_GROUPS

TESTS_AND_COVERAGE_GROUP = "tests-and-coverage"
STATIC_AND_POLICY_GROUP = "static-and-policy"
GROUP_NAMES = REQUIRED_GROUPS

_TEST_CHECK_NAMES = frozenset(("diff-cover", "mutmut-target-ratchet", "pytest-coverage"))
_STATIC_CHECK_NAMES = frozenset(
    (
        "actionlint",
        "architecture-decision",
        "bandit",
        "change-budget",
        "check-jsonschema",
        "deptry",
        "docsync",
        "file-length",
        "import-linter",
        "interrogate",
        "license-check",
        "markdownlint",
        "mutmut",
        "osv-scanner",
        "pip-audit",
        "pylint",
        "pyright",
        "pyright-strict-ratchet",
        "radon-cc-report",
        "radon-mi-report",
        "ruff",
        "ruff-format",
        "sbom",
        "secret-scan",
        "secret-scan-history",
        "semgrep",
        "structure-cohesion",
        "suppression-budget",
        "tach",
        "tach-config",
        "taplo",
        "trivy",
        "typescript-lint",
        "typescript-typecheck",
        "vulture",
        "wemake",
        "xenon-complexity-gate",
        "yamllint",
        "zizmor",
    )
)


class VerificationGroupError(ValueError):
    """Raised when checks cannot be partitioned without ambiguity."""


def checks_for_group(checks: Sequence[Check], group: str) -> list[Check]:
    """Return checks for one group after validating the complete partition."""

    if group not in GROUP_NAMES:
        raise VerificationGroupError(f"unknown verification group: {group}")
    assignments = _assignments(checks)
    return [check for check in checks if assignments[check.name] == group]


def _assignments(checks: Sequence[Check]) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for check in checks:
        if check.name in assignments:
            raise VerificationGroupError(f"duplicate check name: {check.name}")
        assignments[check.name] = _group_for_check(check.name)
    return assignments


def _group_for_check(name: str) -> str:
    base_name = name.partition(":")[0]
    if base_name == "typescript-test" or base_name in _TEST_CHECK_NAMES:
        return TESTS_AND_COVERAGE_GROUP
    if base_name in _STATIC_CHECK_NAMES:
        return STATIC_AND_POLICY_GROUP
    raise VerificationGroupError(f"unassigned check: {name}")
