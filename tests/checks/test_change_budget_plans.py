"""Tests change-budget cohesive change-plan integration."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_maintainer.checks import change_budget as check_change_budget
from agent_maintainer.core.config import MaintainerConfig
from tests.change_plan.test_parser import valid_plan_text


def test_change_budget_active_plan_bends_size_and_test_budget(tmp_path: Path) -> None:
    """Valid plan can bend normal change-budget thresholds."""

    write_change_plan(tmp_path, allow_source_without_test_change=True)
    args = check_change_budget.parse_args(
        ["--warn-lines", "1", "--block-lines", "2", "--warn-files", "1", "--block-files", "1"]
    )
    changes = [
        check_change_budget.FileChange("src/package/a.py", 10, 0),
        check_change_budget.FileChange("src/package/b.py", 10, 0),
    ]

    failures, warnings = check_change_budget.budget_messages(
        args,
        MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True),
        changes,
        [],
        context=check_change_budget.BudgetContext(
            repo_root=tmp_path,
            all_changes=tuple(changes),
        ),
    )

    assert failures == []
    assert any("CHANGE PLAN ACTIVE" in warning for warning in warnings)
    assert not any("Source changed without" in warning for warning in warnings)


def test_change_budget_active_plan_rejects_out_of_scope_path(tmp_path: Path) -> None:
    """Active plan fails when current diff exceeds declared scope."""

    write_change_plan(tmp_path)
    args = check_change_budget.parse_args([])
    changes = [check_change_budget.FileChange("README.md", 1, 0)]

    failures, warnings = check_change_budget.budget_messages(
        args,
        MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True),
        [],
        [],
        context=check_change_budget.BudgetContext(
            repo_root=tmp_path,
            all_changes=tuple(changes),
        ),
    )

    assert warnings == []
    assert any("outside allowed scope" in failure for failure in failures)


def test_change_budget_integration_branch_plan_bends_on_declared_branch(
    tmp_path: Path,
) -> None:
    """Integration branch plans can bend budget on declared branch."""

    write_change_plan(
        tmp_path,
        allow_source_without_test_change=True,
        integration_branch="ratchet/package-migration",
    )
    args = check_change_budget.parse_args(["--block-lines", "2"])
    changes = [check_change_budget.FileChange("src/package/a.py", 10, 0)]

    failures, warnings = check_change_budget.budget_messages(
        args,
        MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True),
        changes,
        [],
        context=check_change_budget.BudgetContext(
            repo_root=tmp_path,
            all_changes=tuple(changes),
            branch_name="ratchet/package-migration",
        ),
    )

    assert failures == []
    assert any("CHANGE PLAN ACTIVE" in warning for warning in warnings)


def test_change_budget_integration_branch_plan_reads_git_branch(
    tmp_path: Path,
) -> None:
    """Integration branch plans validate against real Git branch state."""

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "switch", "-c", "ratchet/package-migration"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    write_change_plan(
        tmp_path,
        allow_source_without_test_change=True,
        integration_branch="ratchet/package-migration",
    )
    args = check_change_budget.parse_args(["--block-lines", "2"])
    changes = [check_change_budget.FileChange("src/package/a.py", 10, 0)]

    failures, warnings = check_change_budget.budget_messages(
        args,
        MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True),
        changes,
        [],
        context=check_change_budget.BudgetContext(
            repo_root=tmp_path,
            all_changes=tuple(changes),
        ),
    )

    assert failures == []
    assert any("CHANGE PLAN ACTIVE" in warning for warning in warnings)


def test_change_budget_integration_branch_plan_fails_on_wrong_branch(
    tmp_path: Path,
) -> None:
    """Integration branch plans cannot bend budget from another branch."""

    write_change_plan(
        tmp_path,
        allow_source_without_test_change=True,
        integration_branch="ratchet/package-migration",
    )
    args = check_change_budget.parse_args(["--block-lines", "2"])
    changes = [check_change_budget.FileChange("src/package/a.py", 10, 0)]

    failures, warnings = check_change_budget.budget_messages(
        args,
        MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=False),
        changes,
        [],
        context=check_change_budget.BudgetContext(
            repo_root=tmp_path,
            all_changes=tuple(changes),
            branch_name="feature/unplanned-change",
        ),
    )

    assert warnings == []
    assert any("does not match integration_branch" in failure for failure in failures)


def test_change_budget_invalid_active_plan_does_not_bend_budget(tmp_path: Path) -> None:
    """Invalid plans fail instead of silently bending thresholds."""

    write_change_plan(tmp_path, expires="2026-06-01")
    args = check_change_budget.parse_args(["--block-lines", "2"])
    changes = [check_change_budget.FileChange("src/package/a.py", 10, 0)]

    failures, _warnings = check_change_budget.budget_messages(
        args,
        MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True),
        changes,
        [],
        context=check_change_budget.BudgetContext(
            repo_root=tmp_path,
            all_changes=tuple(changes),
        ),
    )

    assert any("expired" in failure for failure in failures)
    assert any("Python source diff is too large" in failure for failure in failures)


def write_change_plan(
    root: Path,
    *,
    expires: str = "2099-01-01",
    allow_source_without_test_change: bool = False,
    integration_branch: str = "",
) -> None:
    """Write active change-plan fixture."""

    plan_dir = root / ".agent-maintainer" / "change-plans"
    plan_dir.mkdir(parents=True)
    text = valid_plan_text(expires=expires)
    if integration_branch:
        text = text.replace(
            'kind = "mechanical-migration"',
            'kind = "integration-branch-series"',
        )
        text = text.replace(
            'base_ref = "origin/main"\n',
            (
                'base_ref = "origin/main"\n'
                f'integration_branch = "{integration_branch}"\n'
                'target_branch = "main"\n'
                'merge_strategy = "squash-after-series"\n'
                'expected_units = ["move config modules", "update tests"]\n'
            ),
        )
    if allow_source_without_test_change:
        text = text.replace(
            "allow_source_without_test_change = false",
            "allow_source_without_test_change = true",
        )
    (plan_dir / "package-migration.md").write_text(
        text,
        encoding="utf-8",
    )
