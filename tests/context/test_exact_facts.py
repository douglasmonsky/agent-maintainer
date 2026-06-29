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


def test_ruff_artifact_extracts_path_line_symbol(tmp_path: Path) -> None:
    """Ruff JSON produces exact file, line, column, and rule facts."""
    artifact = tmp_path / "ruff.json"
    artifact.write_text(
        json.dumps(
            [
                {
                    "filename": "src/pkg/app.py",
                    "location": {"row": RUFF_LINE, "column": RUFF_COLUMN},
                    "code": "F401",
                    "message": "Unused import",
                },
            ],
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("ruff", artifact),))

    assert facts == [
        {
            "check": "ruff",
            "path": "src/pkg/app.py",
            "line": RUFF_LINE,
            "column": RUFF_COLUMN,
            "symbol": "F401",
            "message": "Unused import",
            "severity": "error",
        },
    ]


def test_pyright_artifact_extracts_one_based_location(tmp_path: Path) -> None:
    """Pyright JSON zero-based ranges become one-based repair facts."""
    artifact = tmp_path / "pyright.json"
    artifact.write_text(
        json.dumps(
            {
                "generalDiagnostics": [
                    {
                        "file": "src/pkg/app.py",
                        "range": {"start": {"line": 4, "character": 8}},
                        "rule": "reportArgumentType",
                        "message": "Bad argument",
                        "severity": "error",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("pyright", artifact),))

    assert facts[0]["path"] == "src/pkg/app.py"
    assert facts[0]["line"] == PYRIGHT_LINE
    assert facts[0]["column"] == PYRIGHT_COLUMN
    assert facts[0]["symbol"] == "reportArgumentType"


def test_bandit_artifact_extracts_security_fact(tmp_path: Path) -> None:
    """Bandit JSON produces exact security repair facts."""
    artifact = tmp_path / "bandit.json"
    artifact.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "filename": "src/pkg/app.py",
                        "line_number": BANDIT_LINE,
                        "col_offset": 4,
                        "test_id": "B603",
                        "issue_text": "subprocess call",
                        "issue_severity": "HIGH",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("bandit", artifact),))

    assert facts[0]["path"] == "src/pkg/app.py"
    assert facts[0]["line"] == BANDIT_LINE
    assert facts[0]["symbol"] == "B603"
    assert facts[0]["severity"] == "high"


def test_context_pack_uses_structured_artifact_fact(tmp_path: Path) -> None:
    """Context packs expose structured artifact facts before log expansion."""
    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    artifact = log_dir / "ruff.json"
    artifact.write_text(
        json.dumps(
            [
                {
                    "filename": "src/pkg/app.py",
                    "location": {"row": RUFF_LINE, "column": RUFF_COLUMN},
                    "code": "F401",
                    "message": "Unused import",
                },
            ],
        ),
        encoding="utf-8",
    )
    (log_dir / "ruff.log").write_text("ruff failed\n", encoding="utf-8")
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
        encoding="utf-8",
    )

    pack = build_context_pack(
        ContextPackRequest(
            log_dir=log_dir,
            budget=4_000,
            baseline_path=tmp_path / "missing-baseline.json",
        ),
    )
    facts = pack.payload["exact_repair_facts"]

    assert isinstance(facts, list)
    assert facts[0]["path"] == "src/pkg/app.py"
    assert facts[0]["line"] == RUFF_LINE
    assert f"Location: `src/pkg/app.py:{RUFF_LINE}`" in pack.markdown


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
