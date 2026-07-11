"""Tests bounded verifier log context commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_context.failures import FailureRecord
from agent_context.reading.logs import LogRequest, render_log_text, select_log
from agent_maintainer.context import cli as context_cli
from agent_maintainer.context.pack import exact_facts

APP_PATH = "src/pkg/app.py"
TACH_DOMAIN_PATH = "src/agent_maintainer/attention/tach.domain.toml"
TWO_LINES = 2
THREE_LINES = 3
FIVE_LINES = 5
SIX_LINES = 6
WEMAKE_LINE = 12
WEMAKE_COLUMN = 9
XENON_LINE = 98
TWENTY_LINES = 20
THIRTY_CHARS = 30
ENCODING = "utf-8"


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


def test_log_cli_outputs_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def test_architecture_log_extracts_policy_path(tmp_path: Path) -> None:
    """Architecture decision logs point at changed policy files."""

    log_path = tmp_path / "architecture-decision.log"
    log_path.write_text(
        (
            "architecture policy changed without decision note: "
            f"{TACH_DOMAIN_PATH}\n"
            "Add or update a decision note under docs/architecture/decisions/.\n"
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (record_with_log("architecture-decision", log_path),),
    )

    fact = first_fact(facts)
    assert fact["check"] == "architecture-decision"
    assert fact["path"] == TACH_DOMAIN_PATH
    assert fact["symbol"] == "architecture-decision"
    assert "decision note" in str(fact["message"])


def test_change_budget_log_extracts_warning_fact(tmp_path: Path) -> None:
    """Change-budget warning logs produce exact repair facts."""

    log_path = tmp_path / "change-budget.log"
    log_path.write_text(
        (
            "WARN: Source changed without likely relevant test changes. "
            "Likely test files: tests/context/test_logs.py\n"
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("change-budget", log_path),))

    fact = first_fact(facts)
    assert fact["check"] == "change-budget"
    assert fact["path"] is None
    assert fact["symbol"] == "change-budget"
    assert "likely relevant test changes" in str(fact["message"])


def test_ruff_format_log_extracts_targets(tmp_path: Path) -> None:
    """Ruff format logs point at files requiring formatting."""

    log_path = tmp_path / "ruff-format.log"
    log_path.write_text(
        f"Would reformat: {APP_PATH}\n1 file would be reformatted\n",
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("ruff-format", log_path),))

    fact = first_fact(facts)
    assert fact["check"] == "ruff-format"
    assert fact["path"] == APP_PATH
    assert fact["symbol"] == "ruff-format"
    assert fact["message"] == "Run ruff format on this file."


def test_wemake_log_extracts_style_fact(tmp_path: Path) -> None:
    """Wemake flake8 logs produce exact style facts."""

    log_path = tmp_path / "wemake.log"
    log_path.write_text(
        (
            f"{APP_PATH}:{WEMAKE_LINE}:{WEMAKE_COLUMN}: "
            "WPS202 Found too many module members: 22 > 20\n"
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("wemake", log_path),))

    fact = first_fact(facts)
    assert fact["path"] == APP_PATH
    assert fact["line"] == WEMAKE_LINE
    assert fact["column"] == WEMAKE_COLUMN
    assert fact["symbol"] == "WPS202"
    assert "too many module members" in str(fact["message"])


def test_xenon_log_extracts_complexity_fact(tmp_path: Path) -> None:
    """Xenon logs produce exact complex block facts."""

    log_path = tmp_path / "xenon-complexity-gate.log"
    log_path.write_text(
        (f'ERROR:xenon:block "{APP_PATH}:{XENON_LINE} _followthrough_metrics" has a rank of C\n'),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (record_with_log("xenon-complexity-gate", log_path),),
    )

    fact = first_fact(facts)
    assert fact["path"] == APP_PATH
    assert fact["line"] == XENON_LINE
    assert fact["symbol"] == "_followthrough_metrics"
    assert "rank of C" in str(fact["message"])


def first_fact(facts: list[dict[str, object]]) -> dict[str, object]:
    """Return first exact fact fixture output."""

    return facts[0]


def record_with_log(check: str, log_path: Path) -> FailureRecord:
    """Return failure record fixture log-only check."""

    return FailureRecord(
        name=check,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(log_path),
        log_bytes=log_path.stat().st_size,
        expansion_commands=(),
        artifact_paths=(),
    )
