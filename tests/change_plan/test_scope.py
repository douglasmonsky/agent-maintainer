"""Tests cohesive change plan Git scope checks."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_maintainer.change_plan import git_scope, parser
from agent_maintainer.change_plan.models import ChangedPath
from tests.change_plan.test_parser import valid_plan_text


def test_scope_allows_paths_inside_plan(tmp_path: Path) -> None:
    """Allowed source and test paths pass scope validation."""

    plan = parser.parse_plan_text(valid_plan_text(), path=tmp_path / "plan.md")
    changes = (
        ChangedPath(path="src/package/module.py", added=10, deleted=1),
        ChangedPath(path="tests/test_module.py", added=5, deleted=0),
    )

    assert git_scope.scope_issues(plan, changes) == ()


def test_scope_rejects_out_of_plan_path(tmp_path: Path) -> None:
    """Paths outside allowed globs fail scope validation."""

    plan = parser.parse_plan_text(valid_plan_text(), path=tmp_path / "plan.md")
    changes = (ChangedPath(path="README.md", added=1, deleted=0),)

    issues = git_scope.scope_issues(plan, changes)

    assert any("outside allowed scope" in issue.message for issue in issues)


def test_scope_rejects_forbidden_path(tmp_path: Path) -> None:
    """Forbidden paths fail even when other patterns might allow them."""

    plan = parser.parse_plan_text(valid_plan_text(), path=tmp_path / "plan.md")
    changes = (ChangedPath(path="config/prod/settings.toml", added=1, deleted=0),)

    issues = git_scope.scope_issues(plan, changes)

    assert any("forbidden path" in issue.message for issue in issues)


def test_scope_rejects_budget_overrun(tmp_path: Path) -> None:
    """Plan file and line budgets are enforceable."""

    text = valid_plan_text().replace("max_changed_files = 120", "max_changed_files = 1")
    text = text.replace("max_changed_lines = 12000", "max_changed_lines = 3")
    plan = parser.parse_plan_text(text, path=tmp_path / "plan.md")
    changes = (
        ChangedPath(path="src/package/a.py", added=3, deleted=1),
        ChangedPath(path="tests/test_a.py", added=1, deleted=0),
    )

    issues = git_scope.scope_issues(plan, changes)

    assert any("changed file count" in issue.message for issue in issues)
    assert any("changed line count" in issue.message for issue in issues)


def test_scope_requires_tests_for_source_changes(tmp_path: Path) -> None:
    """Source-only changes fail when the plan requires tests."""

    plan = parser.parse_plan_text(valid_plan_text(), path=tmp_path / "plan.md")
    changes = (ChangedPath(path="src/package/module.py", added=10, deleted=1),)

    issues = git_scope.scope_issues(plan, changes)

    assert any("require a test change" in issue.message for issue in issues)


def test_parse_numstat_skips_binary_entries() -> None:
    """Git numstat parsing ignores binary file entries."""

    changes = git_scope.parse_numstat("3\t2\tsrc/app.py\n-\t-\timage.png\n")

    assert changes == (ChangedPath(path="src/app.py", added=3, deleted=2),)


def test_git_numstat_command_supports_staged() -> None:
    """Git numstat command can target staged changes."""

    command = git_scope.git_numstat_command("origin/main", staged=True)

    assert "--cached" in command
    assert command[-1] == "--"


def test_git_changes_uses_numstat_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git change collection parses subprocess stdout."""

    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout="1\t2\tsrc/app.py\n")

    monkeypatch.setattr(git_scope.subprocess, "run", fake_run)

    assert git_scope.git_changes(tmp_path, base_ref="origin/main") == (
        ChangedPath(path="src/app.py", added=1, deleted=2),
    )
