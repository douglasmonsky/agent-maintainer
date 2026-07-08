"""Tests exact repair extraction from plain text logs."""

from __future__ import annotations

from pathlib import Path

from agent_context.failures import FailureRecord
from agent_maintainer.context.pack import exact_facts

APP_PATH = "src/pkg/app.py"
ENCODING = "utf-8"
PYLINT_LINE = 79
PYLINT_COLUMN = 15
VULTURE_LINE = 42


def test_file_length_log_extracts_oversized_file_fact(tmp_path: Path) -> None:
    """File-length logs produce exact oversized-file facts."""

    log_path = tmp_path / "file-length.log"
    log_path.write_text(
        (
            "File length check failed:\n\n"
            f"  {APP_PATH}: new oversized file 501 physical lines, "
            "376 source lines (limits: 500 physical, 375 source)\n"
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("file-length", log_path),))
    fact = first_fact(facts)

    assert fact["path"] == APP_PATH
    assert fact["symbol"] == "file-length"
    assert "new oversized file" in str(fact["message"])


def test_change_budget_log_extracts_blocking_fact(tmp_path: Path) -> None:
    """Change-budget logs produce exact blocking budget facts."""

    log_path = tmp_path / "change-budget.log"
    log_path.write_text(
        (
            "Change budget failed:\n\n"
            "  BLOCK: Python source diff too large: "
            "700 changed lines (block limit: 600).\n"
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("change-budget", log_path),))
    fact = first_fact(facts)

    assert fact["check"] == "change-budget"
    assert fact["path"] is None
    assert fact["symbol"] == "change-budget"
    assert "Python source diff too large" in str(fact["message"])


def test_pylint_log_extracts_symbol_fact(tmp_path: Path) -> None:
    """Pylint default text logs produce exact lint repair facts."""

    log_path = tmp_path / "pylint.log"
    log_path.write_text(
        (
            "************* Module agent_maintainer.wait.codex_rewake\n"
            f"{APP_PATH}:{PYLINT_LINE}:{PYLINT_COLUMN}: W0718: "
            "Catching too general exception "
            "Exception (broad-exception-caught)\n"
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("pylint", log_path),))
    fact = first_fact(facts)

    assert fact["check"] == "pylint"
    assert fact["path"] == APP_PATH
    assert fact["line"] == PYLINT_LINE
    assert fact["column"] == PYLINT_COLUMN
    assert fact["symbol"] == "W0718"
    assert "broad-exception-caught" in str(fact["message"])


def test_vulture_log_extracts_unused_code_fact(tmp_path: Path) -> None:
    """Vulture text logs produce exact unused-code repair facts."""

    log_path = tmp_path / "vulture.log"
    log_path.write_text(
        f"{APP_PATH}:{VULTURE_LINE}: unused function 'stale_helper' (60% confidence)\n",
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record_with_log("vulture", log_path),))
    fact = first_fact(facts)

    assert fact["check"] == "vulture"
    assert fact["path"] == APP_PATH
    assert fact["line"] == VULTURE_LINE
    assert fact["symbol"] == "unused-code"
    assert "stale_helper" in str(fact["message"])


def first_fact(facts: list[dict[str, object]]) -> dict[str, object]:
    """Return first exact fact fixture output."""

    return facts[0]


def record_with_log(check: str, log_path: Path) -> FailureRecord:
    """Return failure record fixture for log-only check."""

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
