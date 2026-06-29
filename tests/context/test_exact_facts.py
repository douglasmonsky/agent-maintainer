"""Tests exact repair fact extraction from structured artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.context import exact_facts
from agent_maintainer.context.failures import FailureRecord
from agent_maintainer.context.packs import ContextPackRequest, build_context_pack

RUFF_LINE = 7
RUFF_COLUMN = 3
PYRIGHT_LINE = 5
PYRIGHT_COLUMN = 9
BANDIT_LINE = 12
PACK_BUDGET = 4_000
APP_PATH = "src/pkg/app.py"
ENCODING = "utf-8"


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
                        "log_path": str(log_dir / "ruff.log"),
                        "artifacts": [str(artifact)],
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
