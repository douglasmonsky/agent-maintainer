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

EXPECTED_FULL_SIGNAL_SCORE = 20


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


def test_target_score_accumulates_all_signal_weights() -> None:
    """Target score preserves every signal contribution."""

    node = ast.parse(
        "def parse_score(value: int) -> int:\n"
        "    if value < 0:\n"
        "        return 0\n"
        "    return value\n"
    ).body[0]
    assert isinstance(node, ast.FunctionDef)
    signals = mutation_targets.TargetSignals(
        complexity=hypothesis_candidates.MIN_BRANCH_COMPLEXITY,
        changed=True,
        likely_test_count=2,
        ratchet_score=5,
    )

    score, reasons = mutation_targets.target_score(node, "parse_score", signals)

    assert score == EXPECTED_FULL_SIGNAL_SCORE
    assert reasons == [
        "changed source",
        "covered by likely focused tests",
        "critical ratchet target",
        "branch complexity 3",
        "pure-ish function",
        "parser/validator/decision logic",
    ]


def test_target_for_function_keeps_threshold_score_and_details() -> None:
    """Target construction keeps inclusive threshold and target detail fields."""

    node = ast.parse("def helper() -> None:\n    print('debug')\n").body[0]
    assert isinstance(node, ast.FunctionDef)

    target = mutation_targets.target_for_function(
        "src/pkg/module.py",
        ("helper", node),
        changed=True,
        likely_test_count=0,
        ratchet_score=0,
    )

    assert target is not None
    assert target.score == mutation_targets.MIN_SCORE
    assert target.complexity == hypothesis_candidates.branch_complexity(node)
    assert (
        target.suggested_focus == "Run a manual mutmut slice focused on src/pkg/module.py::helper; "
        "do not make mutation testing a precommit gate."
    )


def test_target_sort_key_orders_highest_score_first() -> None:
    """Target sort key ranks higher scores before lower scores."""

    low_target = mutation_targets.MutationTarget(
        path="src/pkg/a.py",
        qualname="helper",
        score=4,
        complexity=1,
        reasons=("changed source",),
        suggested_focus="focus low",
    )
    high_target = mutation_targets.MutationTarget(
        path="src/pkg/b.py",
        qualname="parse_value",
        score=10,
        complexity=3,
        reasons=("changed source",),
        suggested_focus="focus high",
    )

    assert sorted(
        (low_target, high_target),
        key=mutation_targets.target_sort_key,
    ) == [high_target, low_target]


def test_targets_for_source_returns_deterministically_sorted_targets(tmp_path: Path) -> None:
    """Source target discovery preserves target sort order."""

    source_file = tmp_path / "src" / "pkg" / "module.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        textwrap.dedent(
            """
            def helper(value: int) -> int:
                return value


            def parse_value(value: int) -> int:
                if value < 0:
                    return 0
                if value > 10:
                    return 10
                return value
            """
        ).lstrip(),
        encoding="utf-8",
    )

    targets = mutation_targets.targets_for_source(
        "src/pkg/module.py",
        tmp_path,
        changed=True,
        likely_test_count=1,
        ratchet_score=0,
    )

    assert [target.qualname for target in targets] == ["parse_value", "helper"]
    assert targets[0].score > targets[1].score


def test_mutation_target_report_passes_ratchet_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report construction passes ratchet context and changed-source status."""

    write_candidate_project(tmp_path)
    calls: list[tuple[MaintainerConfig, Path, str, frozenset[str]]] = []

    def fake_ratchet_path_scores(
        config: MaintainerConfig,
        repo_root: Path,
        base_ref: str,
        changed_paths: frozenset[str],
    ) -> dict[str, int]:
        calls.append((config, repo_root, base_ref, changed_paths))
        return {"src/example_pkg/score.py": 6}

    monkeypatch.setattr(
        mutation_targets,
        "ratchet_path_scores",
        fake_ratchet_path_scores,
    )
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",))

    report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=config,
            repo_root=tmp_path,
            changed_only=True,
            ratchet_enabled=True,
            base_ref="origin/main",
            changed_source=("src/example_pkg/score.py",),
            limit=1,
        )
    )

    assert calls == [(config, tmp_path, "origin/main", frozenset(("src/example_pkg/score.py",)))]
    assert report.changed_only is True
    assert report.changed_source == ("src/example_pkg/score.py",)
    assert len(report.targets) == 1
    assert report.targets[0].path == "src/example_pkg/score.py"
    assert "changed source" in report.targets[0].reasons
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
