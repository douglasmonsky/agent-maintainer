"""Tests cohesive change plan CLI."""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from agent_maintainer import cli as maintainer_cli
from agent_maintainer.change_plan import cli as change_plan_cli
from agent_maintainer.change_plan.models import ChangedPath
from tests.change_plan.test_parser import valid_plan_text


def test_change_plan_new_refuses_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Starter plan creation refuses accidental overwrite."""

    monkeypatch.chdir(tmp_path)

    assert change_plan_cli.main(["new", "package-migration"]) == 0
    assert change_plan_cli.main(["new", "package-migration"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_change_plan_new_can_create_integration_branch_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Starter plan creation supports integration branch series."""

    monkeypatch.chdir(tmp_path)

    assert (
        change_plan_cli.main(
            [
                "new",
                "package-migration",
                "--kind",
                "integration-branch-series",
                "--integration-branch",
                "ratchet/package-migration",
                "--expected-unit",
                "move config modules",
            ]
        )
        == 0
    )

    text = (tmp_path / ".agent-maintainer/change-plans/package-migration.md").read_text()
    assert 'kind = "integration-branch-series"' in text
    assert 'integration_branch = "ratchet/package-migration"' in text
    assert '"move config modules"' in text


def test_change_plan_check_rejects_wrong_integration_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Plan checks fail when branch state does not match metadata."""

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "switch", "-c", "feature/unplanned-change"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(tmp_path)
    assert (
        change_plan_cli.main(
            [
                "new",
                "package-migration",
                "--kind",
                "integration-branch-series",
                "--integration-branch",
                "ratchet/package-migration",
                "--expected-unit",
                "move config modules",
            ]
        )
        == 0
    )

    assert change_plan_cli.main(["check", "--staged"]) == 1
    assert "does not match integration_branch" in capsys.readouterr().out


def test_change_plan_check_validates_without_git_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Check command validates plan files independently from Git scope."""

    monkeypatch.chdir(tmp_path)
    assert change_plan_cli.main(["new", "package-migration"]) == 0

    assert change_plan_cli.main(["check", "--no-git-scope"]) == 0

    assert "PASS change plans" in capsys.readouterr().out


def test_top_level_routes_change_plan_explain(capsys: pytest.CaptureFixture[str]) -> None:
    """Top-level CLI routes the change-plan command."""

    assert maintainer_cli.main(["change-plan", "explain"]) == 0

    assert "Required sections" in capsys.readouterr().out


def test_change_plan_status_reports_empty_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status reports when no plans exist."""

    args = Namespace(plan_dir=tmp_path / "missing")

    assert change_plan_cli.status_command(args) == 0

    assert "No change plans found" in capsys.readouterr().out


def test_change_plan_status_reports_plans_and_parse_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status reports loaded plans and malformed plan files."""

    plan_dir = tmp_path / ".agent-maintainer" / "change-plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "valid.md").write_text(valid_plan_text(), encoding="utf-8")
    (plan_dir / "bad.md").write_text("# bad", encoding="utf-8")

    assert change_plan_cli.status_command(Namespace(plan_dir=plan_dir)) == 1
    output = capsys.readouterr().out

    assert "status=active" in output
    assert "FAIL" in output


def test_change_plan_check_runs_git_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Check command validates current diff against active plan scope."""

    plan_dir = tmp_path / ".agent-maintainer" / "change-plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "valid.md").write_text(valid_plan_text(), encoding="utf-8")

    monkeypatch.setattr(
        change_plan_cli.git_scope,
        "git_changes",
        lambda *_args, **_kwargs: (ChangedPath(path="README.md", added=1, deleted=0),),
    )

    assert (
        change_plan_cli.check_command(
            Namespace(plan_dir=plan_dir, no_git_scope=False, base_ref=None, staged=False)
        )
        == 1
    )

    assert "outside allowed scope" in capsys.readouterr().out
