"""Tests bounded verifier log context commands."""

from __future__ import annotations

import json
from pathlib import Path

from agent_context.reading.logs import LogRequest, render_log_text, select_log
from agent_maintainer.context import cli as context_cli

TWO_LINES = 2
THREE_LINES = 3
FIVE_LINES = 5
SIX_LINES = 6
TWENTY_LINES = 20
THIRTY_CHARS = 30


def test_missing_log_is_graceful(tmp_path: Path) -> None:
    """Missing log returns a clear selection instead of raising."""

    selection = select_log(tmp_path, "pyright")

    assert selection.original_chars == 0
    assert "No log found for pyright" in selection.text


def test_tail_slicing_selects_last_lines(tmp_path: Path) -> None:
    """Tail slicing selects the requested log suffix."""

    write_log(tmp_path, "pyright", line_count=FIVE_LINES)

    selection = select_log(tmp_path, "pyright", LogRequest(tail=TWO_LINES))

    assert selection.text == "line 4\nline 5"
    assert selection.omitted_lines == THREE_LINES


def test_head_tail_slicing_marks_omission(tmp_path: Path) -> None:
    """Head plus tail slicing includes an omission marker."""

    write_log(tmp_path, "pytest-coverage", line_count=SIX_LINES)

    selection = select_log(
        tmp_path,
        "pytest-coverage",
        LogRequest(head=TWO_LINES, tail=TWO_LINES),
    )

    assert selection.text == "line 1\nline 2\n... 2 lines omitted ...\nline 5\nline 6"
    assert selection.omitted_lines == TWO_LINES


def test_line_range_slicing_is_one_based(tmp_path: Path) -> None:
    """Line-range slicing uses one-based inclusive ranges."""

    write_log(tmp_path, "ruff", line_count=FIVE_LINES)

    selection = select_log(tmp_path, "ruff", LogRequest(line_range="2:4"))

    assert selection.text == "line 2\nline 3\nline 4"
    assert selection.omitted_lines == TWO_LINES


def test_large_log_refuses_without_confirmation(tmp_path: Path) -> None:
    """Large log selection refuses unless explicitly confirmed."""

    write_log(tmp_path, "pyright", line_count=TWENTY_LINES)

    selection = select_log(
        tmp_path,
        "pyright",
        LogRequest(tail=TWENTY_LINES, budget=THIRTY_CHARS),
    )

    assert selection.refused is True
    assert "Requested output is approximately" in selection.text
    assert "Estimated tokens:" in selection.text
    assert "context estimate --log pyright" in selection.text
    assert "--confirm-large" in selection.text


def test_log_cli_outputs_json(tmp_path: Path, capsys) -> None:
    """Log subcommand emits JSON output."""

    write_log(tmp_path, "ruff", line_count=THREE_LINES)

    args = ["--log-dir", str(tmp_path), "log", "ruff", "--tail", "2", "--format", "json"]
    assert context_cli.main(args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["check"] == "ruff"
    assert payload["text"] == "line 2\nline 3"


def test_log_text_report_includes_metadata(tmp_path: Path) -> None:
    """Rendered log output includes source metadata."""

    write_log(tmp_path, "ruff", line_count=TWO_LINES)

    output = render_log_text(select_log(tmp_path, "ruff", LogRequest(tail=1)))

    assert "Context log: ruff" in output
    assert "Original chars:" in output
    assert "line 2" in output


def write_log(log_dir: Path, check_name: str, *, line_count: int) -> None:
    """Write verifier log fixture."""

    log_dir.mkdir(parents=True, exist_ok=True)
    text = "\n".join(f"line {index}" for index in range(1, line_count + 1))
    (log_dir / f"{check_name}.log").write_text(text, encoding="utf-8")
