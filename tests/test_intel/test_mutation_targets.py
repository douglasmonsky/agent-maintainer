"""Tests advisory mutation target suggestions."""

from __future__ import annotations

import ast
import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel import cli as maintainer_test_intel_cli
from agent_maintainer.test_intel import hypothesis_candidates, mutation_reporting, mutation_targets
from agent_maintainer.test_intel.cli import main as run_test_intel_cli


def test_mutation_target_report_ranks_branchy_tested_logic(tmp_path: Path) -> None:
    """Branchy parser logic with likely tests ranks as mutation target."""

    write_candidate_project(tmp_path)

    report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            changed_only=False,
            ratchet_enabled=False,
            base_ref="HEAD",
        )
    )

    assert report.targets
    target = report.targets[0]
    assert target.path == "src/example_pkg/score.py"
    assert target.qualname == "parse_score"
    assert "covered by likely focused tests" in target.reasons
    assert any(reason.startswith("branch complexity") for reason in target.reasons)
    assert "parser/validator/decision logic" in target.reasons


def test_mutation_target_renderers_are_advisory(tmp_path: Path) -> None:
    """Text and JSON output make clear mutmut is not run."""

    write_candidate_project(tmp_path)
    report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            changed_only=False,
            ratchet_enabled=False,
            base_ref="HEAD",
        )
    )

    text_output = mutation_reporting.render_text(report)
    payload = json.loads(mutation_reporting.render_json(report))

    assert "Mutation target: src/example_pkg/score.py::parse_score" in text_output
    assert "does not run mutmut" in text_output
    assert payload["targets"][0]["path"] == "src/example_pkg/score.py"
    assert payload["note"] == mutation_targets.ADVISORY_NOTE


def test_mutation_target_cli_changed_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Changed mode limits mutation targets to changed source files."""

    write_candidate_project(tmp_path)
    create_git_repo(tmp_path)
    commit_all(tmp_path)
    source_path = tmp_path / "src" / "example_pkg" / "score.py"
    source_path.write_text(source_text(tmp_path).replace("100", "101"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert run_test_intel_cli(["mutation-targets", "--changed", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_only"] is True
    assert payload["changed_source"] == ["src/example_pkg/score.py"]
    assert payload["targets"][0]["path"] == "src/example_pkg/score.py"
    assert "changed source" in payload["targets"][0]["reasons"]


def test_mutation_targets_ratchet_boost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ratchet paths boost mutation target ranking when requested."""

    write_candidate_project(tmp_path)
    monkeypatch.setattr(
        mutation_targets,
        "ratchet_path_scores",
        lambda *_args, **_kwargs: {"src/example_pkg/score.py": 6},
    )

    report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            changed_only=False,
            ratchet_enabled=True,
            base_ref="HEAD",
        )
    )

    assert report.ratchet_enabled is True
    assert "critical ratchet target" in report.targets[0].reasons


def test_mutation_target_cli_ratchet_without_baseline_is_advisory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ratchet option works even when no baseline is present."""

    write_candidate_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert run_test_intel_cli(["mutation-targets", "--ratchet", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ratchet_enabled"] is True
    assert payload["targets"]


def test_mutation_target_cli_reports_changed_source_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Changed mode reports Git-diff errors."""

    write_candidate_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fail_changed_source(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        raise RuntimeError("git failed")

    monkeypatch.setattr(maintainer_test_intel_cli, "changed_source_paths", fail_changed_source)

    assert run_test_intel_cli(["mutation-targets", "--changed"]) == 1
    assert "git failed" in capsys.readouterr().err


def test_mutation_reporting_empty_changed_output() -> None:
    """Empty changed reports still explain advisory status."""

    report = mutation_targets.MutationTargetReport(
        changed_only=True,
        ratchet_enabled=False,
        changed_source=(),
        targets=(),
    )

    output = mutation_reporting.render_text(report)

    assert "Changed source:" in output
    assert "- <none>" in output
    assert "does not run mutmut" in output
    assert mutation_reporting.render_changed_source(("src/pkg/module.py",)) == [
        "Changed source:",
        "- src/pkg/module.py",
        "",
    ]


def test_mutation_targets_cover_defensive_branches(tmp_path: Path) -> None:
    """Mutation helpers handle malformed inputs and low-signal functions."""

    baseline_path = tmp_path / ".agent-maintainer" / "ratchet-baseline.json"
    baseline_path.parent.mkdir()
    baseline_path.write_text("{", encoding="utf-8")
    config = MaintainerConfig(
        source_roots=("src",),
        test_roots=("tests",),
        ratchet_baseline_path=".agent-maintainer/ratchet-baseline.json",
    )
    malformed_source = tmp_path / "src" / "bad.py"
    malformed_source.parent.mkdir()
    malformed_source.write_text("def broken(:\n", encoding="utf-8")
    low_signal = hypothesis_candidates.iter_public_functions(
        ast.parse("def helper():\n    return 1\n")
    )[0]

    assert mutation_targets.ratchet_path_scores(config, tmp_path, "HEAD", frozenset()) == {}
    assert mutation_targets.ratchet_status_score("new") > 0
    assert mutation_targets.ratchet_status_score("resolved") == 0
    assert (
        mutation_targets.targets_for_source(
            "src/bad.py",
            tmp_path,
            changed=False,
            likely_test_count=0,
            ratchet_score=0,
        )
        == ()
    )
    assert (
        mutation_targets.target_for_function(
            "src/helper.py",
            low_signal,
            changed=False,
            likely_test_count=0,
            ratchet_score=0,
        )
        is None
    )


def write_candidate_project(path: Path) -> None:
    """Write a minimal project with one mutation target."""

    (path / "src" / "example_pkg").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [tool.agent_maintainer]
            source_roots = ["src"]
            test_roots = ["tests"]
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (path / "src" / "example_pkg" / "score.py").write_text(
        textwrap.dedent(
            """
            def parse_score(value: int) -> int:
                if value < 0:
                    return 0
                if value > 100:
                    return 100
                if value == 50:
                    return 51
                return value
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (path / "tests" / "test_score.py").write_text(
        "from example_pkg.score import parse_score\n",
        encoding="utf-8",
    )


def source_text(path: Path) -> str:
    """Return candidate source text."""

    return (path / "src" / "example_pkg" / "score.py").read_text(encoding="utf-8")


def create_git_repo(path: Path) -> None:
    """Initialize Git fixture repo."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.com")
    run_git(path, "config", "user.name", "Agent Maintainer")


def commit_all(path: Path) -> None:
    """Commit fixture files."""

    run_git(path, "add", "pyproject.toml", "src", "tests")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run Git in fixture repository."""

    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
