"""Tests for mutation result test-intelligence CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.test_intel import cli

TOTAL_MUTANTS = 10
KILLED_MUTANTS = 7
SURVIVED_MUTANTS = 3
MUTATION_SCORE = 70.0


def test_mutation_results_cli_renders_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mutation result CLI summarizes exported Mutmut stats."""

    monkeypatch.chdir(tmp_path)
    write_mutmut_stats(tmp_path)

    assert cli.main(["mutation-results"]) == 0

    output = capsys.readouterr().out
    assert "mutmut score 70.00%" in output
    assert "3 survived" in output


def test_mutation_results_cli_renders_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mutation result CLI exposes machine-readable Mutmut stats."""

    monkeypatch.chdir(tmp_path)
    write_mutmut_stats(tmp_path)

    assert cli.main(["mutation-results", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["survived"] == SURVIVED_MUTANTS
    assert payload["score"] == MUTATION_SCORE


def test_mutation_results_cli_fails_when_stats_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing Mutmut stats fail with a compact error."""

    monkeypatch.chdir(tmp_path)

    assert cli.main(["mutation-results"]) == 1

    assert "mutmut stats unavailable" in capsys.readouterr().err


def write_mutmut_stats(path: Path) -> None:
    """Write Mutmut CI stats fixture."""

    stats_path = path / "mutants" / "mutmut-cicd-stats.json"
    stats_path.parent.mkdir()
    stats_path.write_text(
        json.dumps(
            {
                "killed": KILLED_MUTANTS,
                "survived": SURVIVED_MUTANTS,
                "total": TOTAL_MUTANTS,
                "no_tests": 0,
                "skipped": 0,
                "suspicious": 0,
                "timeout": 0,
                "check_was_interrupted_by_user": 0,
                "segfault": 0,
            }
        ),
        encoding="utf-8",
    )
