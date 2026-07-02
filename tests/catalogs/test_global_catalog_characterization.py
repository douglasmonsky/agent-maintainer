"""Characterization tests for global check catalog helpers."""

from __future__ import annotations

from agent_maintainer.catalogs.global_checks import (
    architecture_checks,
    reviewability_checks,
    workflow_checks,
)
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import CI_PROFILE, FAST_PROFILE, FULL_PROFILE


def test_global_reviewability_checks_preserve_names_and_profiles() -> None:
    """Pin Python-backed reviewability checks outside ecosystem providers."""
    checks = reviewability_checks(MaintainerConfig(), "HEAD", staged=True)

    assert [check.name for check in checks] == [
        "file-length",
        "structure-cohesion",
        "change-budget",
        "change-budget",
        "change-budget",
        "change-budget",
        "suppression-budget",
    ]
    assert checks[0].profiles == {FAST_PROFILE, "precommit", FULL_PROFILE, CI_PROFILE}
    assert "--staged" in checks[2].command
    assert checks[-1].required_paths == (".git",)


def test_reviewability_checks_call_python_policy_modules() -> None:
    """Current reviewability policy remains Python-backed during beta."""
    checks = reviewability_checks(MaintainerConfig(), "HEAD", staged=True)
    modules = {
        check.name: check.command[2]
        for check in checks
        if check.command[:2] and check.command[1] == "-m"
    }

    assert modules["file-length"] == "agent_maintainer.checks.file_lengths"
    assert modules["structure-cohesion"] == "agent_maintainer.checks.structure"
    assert modules["change-budget"] == "agent_maintainer.checks.change_budget"
    assert modules["suppression-budget"] == "agent_maintainer.checks.suppression_budget"


def test_global_architecture_and_workflow_checks_remain_separate() -> None:
    """Pin global architecture/workflow helpers before more provider work."""
    config = MaintainerConfig(architecture_tool="tach", mode="fresh-strict")
    architecture = architecture_checks(config, "HEAD", staged=True)
    workflow = workflow_checks()

    assert [check.name for check in architecture] == [
        "tach-config",
        "architecture-decision",
        "tach",
    ]
    assert "--staged" in architecture[1].command
    assert [check.name for check in workflow] == ["actionlint", "zizmor"]
