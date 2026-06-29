"""Tests safe verifier failure context commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.context import cli as context_cli
from agent_maintainer.context.failures import failure_records, render_failures_text

BOUNDED_OUTPUT_MAX_CHARS = 180


def test_context_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    """Context command help prints usage."""

    with pytest.raises(SystemExit) as exc_info:
        context_cli.main(["--help"])

    assert exc_info.value.code == 0
    assert "context" in capsys.readouterr().out


def test_failure_records_are_grouped_by_priority(tmp_path: Path) -> None:
    """Failures are sorted by repair priority before style failures."""

    write_manifest(tmp_path, failed_checks=("ruff", "pytest-coverage", "pyright"))

    records = failure_records(tmp_path)

    assert [record.name for record in records] == ["pyright", "pytest-coverage", "ruff"]
    assert [record.category for record in records] == ["type", "test", "style/noise"]


def test_failures_text_is_bounded(tmp_path: Path) -> None:
    """Failure report obeys configured character budget."""

    write_manifest(tmp_path, failed_checks=("ruff", "pyright"))

    output = render_failures_text(failure_records(tmp_path), log_dir=tmp_path, budget=80)

    assert len(output) < BOUNDED_OUTPUT_MAX_CHARS
    assert "context failures omitted" in output


def test_failures_cli_outputs_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Failures subcommand emits stable JSON."""

    write_manifest(tmp_path, failed_checks=("pyright",))

    assert context_cli.main(["--log-dir", str(tmp_path), "failures", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["manifest_path"] == str(tmp_path / "manifest.json")
    assert payload["failures"][0]["name"] == "pyright"
    assert payload["failures"][0]["expansion_commands"] == [
        "python -m agent_maintainer context log pyright --tail 120",
    ]


def test_failures_missing_manifest_is_graceful(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing verifier manifest returns a clear message."""

    assert context_cli.main(["--log-dir", str(tmp_path), "failures"]) == 0

    assert "No verifier manifest found" in capsys.readouterr().out


def write_manifest(path: Path, *, failed_checks: tuple[str, ...]) -> None:
    """Write verifier manifest fixture."""

    checks = [
        {
            "name": name,
            "status": "failed",
            "exit_code": 1,
            "log_path": f".verify-logs/{name}.log",
            "log_bytes": 100,
            "expansion_commands": [
                f"python -m agent_maintainer context log {name} --tail 120",
            ],
        }
        for name in failed_checks
    ]
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text(json.dumps({"checks": checks}), encoding="utf-8")
