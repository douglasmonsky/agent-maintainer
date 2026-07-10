"""Tests for attention-weighted context packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from agent_context.pack_rendering import render_pack_pointer
from agent_maintainer.context.pack.builder import ContextPackRequest, write_context_pack

APP_PATH = "src/pkg/app.py"
OTHER_PATH = "docs/guide.md"
PRIMARY_SCORE = 0.9


def test_context_pack_works_without_attention_ledger(tmp_path: Path) -> None:
    """Missing ledger keeps context packs compatible and explicit."""
    log_dir = tmp_path / ".verify-logs"
    write_manifest(log_dir, "ruff")
    write_log(log_dir, "ruff", "ruff failed\n")

    pack = write_context_pack(ContextPackRequest(log_dir=log_dir, budget=8_000))

    assert pack.payload["attention"] == {
        "available": False,
        "ledger_path": str(log_dir / "attention" / "files.json"),
        "entries": [],
        "risk_notes": [],
    }
    assert "## Attention" in pack.markdown
    assert "Attention ledger unavailable" in pack.markdown


def test_context_pack_attaches_attention_to_exact_file_fact(tmp_path: Path) -> None:
    """Facts mentioning files receive attention score metadata."""
    log_dir = tmp_path / ".verify-logs"
    write_ledger(log_dir, APP_PATH)
    write_ruff_manifest(log_dir, APP_PATH)

    pack = write_context_pack(ContextPackRequest(log_dir=log_dir, budget=8_000))
    facts = pack.payload["exact_repair_facts"]

    assert isinstance(facts, list)
    fact = cast(dict[str, Any], facts[0])
    attention = cast(dict[str, Any], pack.payload["attention"])
    entries = cast(list[dict[str, Any]], attention["entries"])
    assert fact["attention"]["score"] == PRIMARY_SCORE
    assert entries[0]["path"] == APP_PATH
    pointer = render_pack_pointer(pack.payload, display_path=str(pack.markdown_path))
    assert "Attention notes:" in pointer
    assert APP_PATH in pointer


def test_context_pack_attention_falls_back_to_selected_log_paths(tmp_path: Path) -> None:
    """When facts lack paths, selected log text can still select attention entries."""
    log_dir = tmp_path / ".verify-logs"
    write_ledger(log_dir, APP_PATH)
    write_manifest(log_dir, "custom-check")
    write_log(log_dir, "custom-check", f"failure mentions {APP_PATH}\n")

    pack = write_context_pack(ContextPackRequest(log_dir=log_dir, budget=8_000))

    attention = cast(dict[str, Any], pack.payload["attention"])
    entries = cast(list[dict[str, Any]], attention["entries"])
    assert entries[0]["path"] == APP_PATH
    assert APP_PATH in pack.markdown


def write_ledger(log_dir: Path, primary_path: str) -> None:
    """Write attention ledger fixture."""
    ledger = {
        "schema_version": 1,
        "target": str(log_dir.parent),
        "file_count": 2,
        "inputs": {},
        "files": [
            {
                "path": primary_path,
                "score": PRIMARY_SCORE,
                "components": {"git_changed": 1.0},
                "reasons": (f"{primary_path}: changed in current worktree or index",),
            },
            {
                "path": OTHER_PATH,
                "score": 0.2,
                "components": {"path": 0.35},
                "reasons": (f"{OTHER_PATH}: important repository path",),
            },
        ],
    }
    path = log_dir / "attention" / "files.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger), encoding="utf-8")


def write_ruff_manifest(log_dir: Path, path: str) -> None:
    """Write manifest with Ruff structured artifact."""
    artifact = log_dir / "ruff.json"
    artifact.write_text(
        json.dumps(
            [
                {
                    "filename": path,
                    "location": {"row": 3, "column": 1},
                    "code": "F401",
                    "message": "Unused import",
                }
            ]
        ),
        encoding="utf-8",
    )
    write_log(log_dir, "ruff", "ruff failed\n")
    write_manifest(log_dir, "ruff", artifacts=(Path(artifact.name),))


def write_manifest(
    log_dir: Path,
    check_name: str,
    *,
    artifacts: tuple[Path, ...] = (),
) -> None:
    """Write verifier manifest fixture."""
    log_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "checks": [
            {
                "name": check_name,
                "status": "failed",
                "exit_code": 1,
                "log_path": str(log_dir / f"{check_name}.log"),
                "artifacts": [str(path) for path in artifacts],
            }
        ]
    }
    (log_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def write_log(log_dir: Path, check_name: str, text: str) -> None:
    """Write verifier log fixture."""
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{check_name}.log").write_text(text, encoding="utf-8")
