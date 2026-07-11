"""Tests exact repair fact extraction from structured artifacts."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agent_context.failures import FailureRecord
from agent_maintainer.context.pack import exact_facts
from agent_maintainer.context.pack import fact_parsers as old_registry
from agent_maintainer.context.pack import fact_payloads as old_payloads
from agent_maintainer.context.pack import lint_fact_parsers as old_lint_parsers
from agent_maintainer.context.pack import log_fact_parsers as old_log_parsers
from agent_maintainer.context.pack import pytest_fact_parsers as old_pytest_parsers
from agent_maintainer.context.pack import (
    typescript_fact_parsers as old_typescript_parsers,
)
from agent_maintainer.context.pack.builder import ContextPackRequest, build_context_pack
from agent_repair_facts import registry
from agent_repair_facts.parsers import lint, logs, typescript
from agent_repair_facts.parsers import pytest as pytest_parsers
from agent_repair_facts.payloads import fact_payload

RUFF_LINE = 7
RUFF_COLUMN = 3
PYRIGHT_LINE = 5
PYRIGHT_COLUMN = 9
BANDIT_LINE = 12
JUNIT_LINE = 21
COVERAGE_MISSING_LINE = 44
PACK_BUDGET = 4_000
APP_PATH = "src/pkg/app.py"
ENCODING = "utf-8"


def test_repair_fact_package_exports_registry_functions() -> None:
    """The new package exposes the active repair-fact registry."""
    assert registry.artifact_facts("unknown", Path("missing.json")) == []
    assert registry.log_facts("unknown", Path("missing.log")) == []


def test_exact_fact_budget_deduplicates_manifest_artifact_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate manifest paths cannot multiply parser reads."""

    artifact = tmp_path / "ruff.json"
    artifact.write_text("[]\n", encoding=ENCODING)
    calls: list[Path] = []

    def fake_artifact_facts(
        check: str,
        path: Path,
        text: str,
    ) -> list[dict[str, object]]:
        calls.append(path)
        assert text == "[]\n"
        return [fact_payload({"check": check, "message": "one fact"})]

    monkeypatch.setattr(registry, "artifact_facts_from_text", fake_artifact_facts)
    duplicate_record = replace(
        record("ruff", artifact),
        artifact_paths=(str(artifact),) * 250,
    )

    facts = exact_facts.repair_facts(tmp_path, (duplicate_record,))

    assert len(facts) == 1
    assert calls == [artifact]


def test_old_context_pack_registry_imports_are_compatibility_shims() -> None:
    """Old context-pack parser imports remain stable through shims."""
    assert old_registry.artifact_facts is registry.artifact_facts
    assert old_registry.log_facts is registry.log_facts
    assert old_payloads.fact_payload is fact_payload
    assert old_lint_parsers.ruff_facts is lint.ruff_facts
    assert old_log_parsers.file_length_facts is logs.file_length_facts
    assert old_pytest_parsers.pytest_artifact_facts is pytest_parsers.pytest_artifact_facts
    assert old_typescript_parsers.typescript_lint_facts is (typescript.typescript_lint_facts)


def test_ruff_artifact_extracts_path_line_symbol(tmp_path: Path) -> None:
    """Ruff JSON produces exact file, line, column, and rule facts."""
    artifact = tmp_path / "ruff.json"
    artifact.write_text(
        json.dumps(
            [
                {
                    "filename": APP_PATH,
                    "location": {"row": RUFF_LINE, "column": RUFF_COLUMN},
                    "code": "F401",
                    "message": "Unused import",
                },
            ],
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record("ruff", artifact),))

    assert facts == [
        {
            "check": "ruff",
            "path": APP_PATH,
            "line": RUFF_LINE,
            "column": RUFF_COLUMN,
            "symbol": "F401",
            "message": "Unused import",
            "severity": "error",
        },
    ]


def test_pyright_artifact_is_one_based(tmp_path: Path) -> None:
    """Pyright JSON zero-based ranges become one-based repair facts."""
    artifact = tmp_path / "pyright.json"
    artifact.write_text(
        json.dumps(
            {
                "generalDiagnostics": [
                    {
                        "file": APP_PATH,
                        "range": {"start": {"line": 4, "character": 8}},
                        "rule": "reportArgumentType",
                        "message": "Bad argument",
                        "severity": "error",
                    },
                ],
            },
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record("pyright", artifact),))
    fact = first_fact(facts)

    assert fact["path"] == APP_PATH
    assert fact["line"] == PYRIGHT_LINE
    assert fact["column"] == PYRIGHT_COLUMN
    assert fact["symbol"] == "reportArgumentType"


def test_bandit_artifact_extracts_security_fact(tmp_path: Path) -> None:
    """Bandit JSON produces exact security repair facts."""
    artifact = tmp_path / "bandit.json"
    artifact.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "filename": APP_PATH,
                        "line_number": BANDIT_LINE,
                        "col_offset": 4,
                        "test_id": "B603",
                        "issue_text": "subprocess call",
                        "issue_severity": "HIGH",
                    },
                ],
            },
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record("bandit", artifact),))
    fact = first_fact(facts)

    assert fact["path"] == APP_PATH
    assert fact["line"] == BANDIT_LINE
    assert fact["symbol"] == "B603"
    assert fact["severity"] == "high"


def test_relative_artifact_uses_log_dir(tmp_path: Path) -> None:
    """Relative artifact paths resolve against log directory by filename."""
    artifact = tmp_path / "ruff.json"
    artifact.write_text(
        json.dumps(
            [
                {
                    "filename": APP_PATH,
                    "location": {"row": RUFF_LINE, "column": RUFF_COLUMN},
                    "code": "F401",
                    "message": "Unused import",
                },
            ],
        ),
        encoding=ENCODING,
    )

    failure = FailureRecord(
        name="ruff",
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(tmp_path / "ruff.log"),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=("logs/ruff.json",),
    )

    facts = exact_facts.repair_facts(tmp_path, (failure,))
    fact = first_fact(facts)

    assert fact["path"] == APP_PATH
    assert fact["line"] == RUFF_LINE


def test_missing_artifact_uses_generic(tmp_path: Path) -> None:
    """Missing structured artifacts fall back to generic failure facts."""
    facts = exact_facts.repair_facts(tmp_path, (record("ruff", tmp_path / "missing.json"),))

    assert facts == [
        {
            "check": "ruff",
            "path": None,
            "line": None,
            "column": None,
            "symbol": None,
            "message": "ruff failed with exit code 1",
            "severity": "error",
        },
    ]


def test_malformed_artifacts_use_generic(tmp_path: Path) -> None:
    """Malformed structured artifacts do not replace generic failure facts."""
    ruff_artifact = write_json(tmp_path / "ruff.json", {})
    pyright_payload_artifact = write_json(tmp_path / "pyright-payload.json", [])
    pyright_diagnostics_artifact = write_json(
        tmp_path / "pyright-diagnostics.json",
        {"generalDiagnostics": {}},
    )
    bandit_payload_artifact = write_json(tmp_path / "bandit-payload.json", [])
    bandit_results_artifact = write_json(tmp_path / "bandit-results.json", {"results": {}})

    cases = (
        ("ruff", ruff_artifact),
        ("pyright", pyright_payload_artifact),
        ("pyright", pyright_diagnostics_artifact),
        ("bandit", bandit_payload_artifact),
        ("bandit", bandit_results_artifact),
    )

    for check, artifact in cases:
        facts = exact_facts.repair_facts(tmp_path, (record(check, artifact),))
        fact = first_fact(facts)

        assert fact["check"] == check
        assert fact["path"] is None
        assert fact["symbol"] is None
        assert fact["message"] == f"{check} failed with exit code 1"


def test_pyright_fact_tolerates_missing_range(tmp_path: Path) -> None:
    """Pyright diagnostics without ranges still produce useful facts."""
    artifact = tmp_path / "pyright.json"
    artifact.write_text(
        json.dumps(
            {
                "generalDiagnostics": [
                    {
                        "file": APP_PATH,
                        "rule": "reportUnknownMemberType",
                        "message": "Unknown member",
                    },
                ],
            },
        ),
        encoding=ENCODING,
    )

    facts = exact_facts.repair_facts(tmp_path, (record("pyright", artifact),))
    fact = first_fact(facts)

    assert fact["path"] == APP_PATH
    assert fact["line"] is None
    assert fact["column"] is None
    assert fact["symbol"] == "reportUnknownMemberType"


def test_pytest_junit_artifact_extracts_failed_test_fact(tmp_path: Path) -> None:
    """Pytest JUnit XML produces test failure repair facts."""

    junit = tmp_path / "pytest-junit.xml"
    coverage = write_json(
        tmp_path / "coverage.json",
        {"files": {APP_PATH: {"missing_lines": [COVERAGE_MISSING_LINE, 45]}}},
    )
    junit.write_text(
        (
            '<testsuite><testcase classname="tests.test_app" '
            f'name="test_app" file="{APP_PATH}" line="{JUNIT_LINE}">'
            '<failure message="assert 1 == 2">failure detail</failure>'
            "</testcase></testsuite>"
        ),
        encoding=ENCODING,
    )
    failure = FailureRecord(
        name="pytest-coverage",
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(tmp_path / "pytest.log"),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(coverage), str(junit)),
    )

    facts = exact_facts.repair_facts(tmp_path, (failure,))
    fact = first_fact(facts)

    assert fact["check"] == "pytest-coverage"
    assert fact["path"] == APP_PATH
    assert fact["line"] == JUNIT_LINE
    assert fact["symbol"] == "pytest-failure"
    assert "tests.test_app::test_app" in str(fact["message"])


def test_coverage_json_artifact_extracts_missing_line_fact(tmp_path: Path) -> None:
    """Coverage JSON produces missing-line repair facts."""

    artifact = write_json(
        tmp_path / "coverage.json",
        {"files": {APP_PATH: {"missing_lines": [COVERAGE_MISSING_LINE, 45]}}},
    )

    facts = exact_facts.repair_facts(tmp_path, (record("pytest-coverage", artifact),))
    fact = first_fact(facts)

    assert fact["check"] == "pytest-coverage"
    assert fact["path"] == APP_PATH
    assert fact["line"] == COVERAGE_MISSING_LINE
    assert fact["symbol"] == "coverage"
    assert fact["message"] == "2 uncovered line(s) in file."


def test_pack_uses_structured_fact(tmp_path: Path) -> None:
    """Context packs expose structured artifact facts before log expansion."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    artifact = log_dir / "ruff.json"
    artifact.write_text(
        json.dumps(
            [
                {
                    "filename": APP_PATH,
                    "location": {"row": RUFF_LINE, "column": RUFF_COLUMN},
                    "code": "F401",
                    "message": "Unused import",
                },
            ],
        ),
        encoding=ENCODING,
    )
    (log_dir / "ruff.log").write_text("ruff failed\n", encoding=ENCODING)
    (log_dir / "manifest.json").write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "name": "ruff",
                        "status": "failed",
                        "exit_code": 1,
                        "log_path": str(Path(log_dir.name) / "ruff.log"),
                        "artifacts": [str(Path(log_dir.name) / artifact.name)],
                    },
                ],
            },
        ),
        encoding=ENCODING,
    )

    pack = build_context_pack(
        ContextPackRequest(
            log_dir=log_dir,
            budget=PACK_BUDGET,
            baseline_path=tmp_path / "missing-baseline.json",
        ),
    )
    facts = pack.payload["exact_repair_facts"]

    assert isinstance(facts, list)
    fact = first_fact(facts)
    assert fact["path"] == APP_PATH
    assert fact["line"] == RUFF_LINE
    assert f"Location: `{APP_PATH}:{RUFF_LINE}`" in pack.markdown


def write_json(path: Path, payload: object) -> Path:
    """Write JSON fixture and return the path."""
    path.write_text(json.dumps(payload), encoding=ENCODING)
    return path


def first_fact(facts: list[dict[str, object]]) -> dict[str, object]:
    """Return the first exact fact from fixture output."""
    return facts[0]


def record(check: str, artifact: Path) -> FailureRecord:
    """Return failure record fixture with one artifact."""
    return FailureRecord(
        name=check,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(artifact.with_suffix(".log")),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(artifact),),
    )
