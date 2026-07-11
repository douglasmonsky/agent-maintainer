"""Tests context expansion size estimates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_context import estimate as estimate_module
from agent_context.estimate import (
    EstimateRequest,
    estimate_context,
    render_estimate_text,
)
from agent_context.failures import failure_records
from agent_context.reading.files import FileRequest
from agent_context.reading.logs import LogRequest, select_log
from agent_maintainer.context import cli as context_cli
from agent_maintainer.context import estimate as old_estimate
from agent_maintainer.context import failures as old_failures
from agent_maintainer.context.reading import files as old_files
from agent_maintainer.context.reading import logs as old_logs
from tests.support.callbacks import constant_callback

FOUR_CHARS = 4
ONE_TOKEN = 1
TWO_LINES = 2
FIVE_LINES = 5
DIFF_TEXT = " README.md | 2 ++\n 1 file changed\n"


def test_old_context_reading_imports_delegate_to_agent_context() -> None:
    """Old context reader imports remain compatibility shims."""
    assert old_estimate.EstimateRequest is EstimateRequest
    assert old_failures.failure_records is failure_records
    assert old_files.FileRequest is FileRequest
    assert old_logs.select_log is select_log


def test_file_estimate_counts_chars_and_tokens(tmp_path: Path) -> None:
    """File estimate reports character and approximate token count."""

    path = tmp_path / "sample.py"
    path.write_text("abcd", encoding="utf-8")

    estimate = estimate_context(
        EstimateRequest(log_dir=tmp_path, file_path=path, workspace_root=tmp_path),
    )

    assert estimate.label == f"file {path}"
    assert estimate.chars == FOUR_CHARS
    assert estimate.tokens == ONE_TOKEN


def test_log_estimate_uses_requested_tail(tmp_path: Path) -> None:
    """Log estimate uses same slicing rules as log expansion."""

    write_log(tmp_path, "pyright", line_count=FIVE_LINES)
    expected = "line 4\nline 5"

    estimate = estimate_context(
        EstimateRequest(
            log_dir=tmp_path,
            log_check="pyright",
            log_request=LogRequest(tail=TWO_LINES),
            workspace_root=tmp_path,
        ),
    )

    assert estimate.label == "log pyright"
    assert estimate.chars == len(expected)


def test_log_estimate_resolves_manifest_from_explicit_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest paths do not inherit an unrelated process working directory."""

    workspace = tmp_path / "workspace"
    log_dir = workspace / ".verify-logs"
    other = tmp_path / "other"
    other.mkdir()
    write_log(log_dir, "pyright", line_count=TWO_LINES)
    (log_dir / "manifest.json").write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "name": "pyright",
                        "log_path": ".verify-logs/pyright.log",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(other)

    estimate = estimate_context(
        EstimateRequest(
            log_dir=log_dir,
            log_check="pyright",
            workspace_root=workspace,
        ),
    )

    assert estimate.chars > 0


def test_diff_summary_estimate_uses_git_diff_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diff summary estimate uses stat output."""

    monkeypatch.setattr(estimate_module, "run_git_diff", constant_callback(DIFF_TEXT))

    estimate = estimate_context(
        EstimateRequest(log_dir=tmp_path, diff=True, diff_summary=True),
    )

    assert estimate.label == "diff summary"
    assert estimate.chars == len(DIFF_TEXT)


def test_estimate_text_reports_recommendation(tmp_path: Path) -> None:
    """Text estimate includes budget and recommendation."""

    path = tmp_path / "sample.py"
    path.write_text("abcd", encoding="utf-8")

    output = render_estimate_text(
        estimate_context(
            EstimateRequest(log_dir=tmp_path, file_path=path, workspace_root=tmp_path),
        ),
    )

    assert "Estimated output: file" in output
    assert "tokens: ~1" in output
    assert "Recommended:" in output


def test_file_estimate_refuses_outside_workspace_content(tmp_path: Path) -> None:
    """File size estimates cannot disclose or size an outside file."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("ESTIMATE-OUTSIDE-CANARY", encoding="utf-8")

    estimate = estimate_context(
        EstimateRequest(
            log_dir=workspace,
            file_path=Path("../outside.txt"),
            workspace_root=workspace,
        ),
    )

    assert estimate.chars == 0
    assert estimate.tokens == 0


def test_estimate_cli_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Estimate subcommand emits stable JSON."""

    path = tmp_path / "sample.py"
    path.write_text("abcd", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert (
        context_cli.main(
            ["--log-dir", str(tmp_path), "estimate", "--file", str(path), "--format", "json"],
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["label"] == f"file {path}"
    assert payload["chars"] == FOUR_CHARS


def write_log(log_dir: Path, check_name: str, *, line_count: int) -> None:
    """Write verifier log fixture."""

    log_dir.mkdir(parents=True, exist_ok=True)
    text = "\n".join(f"line {index}" for index in range(1, line_count + 1))
    (log_dir / f"{check_name}.log").write_text(text, encoding="utf-8")
