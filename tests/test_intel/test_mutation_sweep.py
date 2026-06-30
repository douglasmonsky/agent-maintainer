"""Tests advisory mutation sweep planning."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel import (
    cli,
    mutation_sweep,
    mutation_sweep_cli,
    mutation_sweep_reporting,
)

SCORE_COVERAGE = 90.0
SCORE_CHURN = 5
PLAIN_COVERAGE = 10.0


def test_mutation_sweep_ranks_changed_covered_churned_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changed, covered, churned branch logic ranks first."""

    write_sweep_project(tmp_path)
    monkeypatch.setattr(
        mutation_sweep,
        "git_churn_count",
        lambda _repo_root, path: SCORE_CHURN if path.endswith("score.py") else 0,
    )

    report = mutation_sweep.build_mutation_sweep_report(
        mutation_sweep.MutationSweepRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            base_ref="HEAD",
            changed_only=False,
            changed_source=("src/example_pkg/score.py",),
            limit=2,
        )
    )

    assert report.candidates
    top_candidate = report.candidates[0]
    assert top_candidate.path == "src/example_pkg/score.py"
    assert top_candidate.changed is True
    assert top_candidate.coverage_percent == SCORE_COVERAGE
    assert top_candidate.churn == SCORE_CHURN
    assert "tests/test_score.py" in top_candidate.likely_tests
    assert top_candidate.suggested_only_mutate == "src/example_pkg/score.py"
    assert "changed source" in top_candidate.reasons
    assert "90.0% file coverage" in top_candidate.reasons


def test_mutation_sweep_renderers_include_commands(tmp_path: Path) -> None:
    """Text and JSON renderers include stop conditions and repair commands."""

    write_sweep_project(tmp_path)
    report = mutation_sweep.build_mutation_sweep_report(
        mutation_sweep.MutationSweepRequest(
            config=MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
            repo_root=tmp_path,
            base_ref="HEAD",
            changed_only=True,
            changed_source=("src/example_pkg/score.py",),
            limit=1,
            time_budget_minutes=7,
            survivor_threshold=2,
        )
    )

    text_output = mutation_sweep_reporting.render_text(report)
    payload = json.loads(mutation_sweep_reporting.render_json(report))

    assert "Mutation sweep candidates" in text_output
    assert "time budget 7 minute(s)" in text_output
    assert "Suggested only_mutate: src/example_pkg/score.py" in text_output
    assert mutation_sweep.MUTMUT_MANUAL_COMMAND in text_output
    assert payload["stop_conditions"][0] == "time budget 7 minute(s)"
    assert payload["candidates"][0]["suggested_only_mutate"] == "src/example_pkg/score.py"


def test_mutation_sweep_cli_changed_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI reports changed-source errors cleanly."""

    def fail_changed_source(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        raise RuntimeError("git failed")

    monkeypatch.setattr(mutation_sweep_cli, "changed_source_paths", fail_changed_source)

    assert cli.main(["mutation-sweep", "--changed"]) == 1
    assert "git failed" in capsys.readouterr().err


def write_sweep_project(path: Path) -> None:
    """Write minimal project with two candidate modules."""

    source_root = path / "src" / "example_pkg"
    tests_root = path / "tests"
    source_root.mkdir(parents=True)
    tests_root.mkdir()
    (source_root / "score.py").write_text(score_source(), encoding="utf-8")
    (source_root / "plain.py").write_text(plain_source(), encoding="utf-8")
    (tests_root / "test_score.py").write_text(
        "from example_pkg.score import parse_score\n",
        encoding="utf-8",
    )
    (path / "coverage.json").write_text(
        json.dumps(
            {
                "files": {
                    "src/example_pkg/score.py": {
                        "summary": {
                            "percent_covered": SCORE_COVERAGE,
                        },
                    },
                    "src/example_pkg/plain.py": {
                        "summary": {
                            "percent_covered": PLAIN_COVERAGE,
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def score_source() -> str:
    """Return branchy candidate source."""

    return textwrap.dedent(
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
    ).lstrip()


def plain_source() -> str:
    """Return lower-value candidate source."""

    return textwrap.dedent(
        """
        def normalize(value: int) -> int:
            if value < 0:
                return 0
            return value
        """
    ).lstrip()
