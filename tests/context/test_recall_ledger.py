"""Tests for context recall ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.context import cli, recall


def test_recall_ledger_adds_and_filters_items(tmp_path: Path) -> None:
    """Ledger stores newest matching items without raw transcript expansion."""
    log_dir = tmp_path / ".verify-logs"

    decision = recall.add_item(
        log_dir,
        recall.RecallInput(
            kind="decision",
            summary="Use compact repair capsules",
            paths=("src/agent_maintainer/verify/quiet.py",),
            artifacts=(".verify-logs/runs/run-id/manifest.json",),
            commands=("python -m agent_maintainer context recall --kind decision",),
            tags=("quiet-output",),
            values=("profile=precommit",),
        ),
    )
    recall.add_item(
        log_dir,
        recall.RecallInput(kind="task", summary="Follow up on docs"),
    )

    assert (log_dir / "context" / "ledger.jsonl").exists()
    decisions = recall.recall_items(log_dir, kind="decision")
    assert decisions == [decision]
    assert recall.recall_items(log_dir, query="quiet-output") == [decision]

    rendered = recall.render_recall_text(decisions)
    assert "Context recall" in rendered
    assert "Use compact repair capsules" in rendered
    assert ".verify-logs/runs/run-id/manifest.json" in rendered
    assert "python -m agent_maintainer context recall" in rendered


def test_recall_ledger_json_roundtrip(tmp_path: Path) -> None:
    """JSON rendering exposes compact, stable fields."""
    item = recall.add_item(
        tmp_path,
        recall.RecallInput(
            kind="constraint",
            summary="Do not paste raw logs",
        ),
    )

    payload = json.loads(recall.render_item_json(item))
    assert payload["kind"] == "constraint"
    assert payload["summary"] == "Do not paste raw logs"
    assert payload["item_id"]

    recalled_payload = json.loads(recall.render_items_json(recall.read_items(tmp_path)))
    assert recalled_payload["items"][0]["item_id"] == item.item_id


def test_recall_ledger_validates_kind_and_summary(tmp_path: Path) -> None:
    """Invalid records fail before writing JSONL."""
    with pytest.raises(ValueError, match="kind must be one of"):
        recall.add_item(
            tmp_path,
            recall.RecallInput(kind="thought", summary="not allowed"),
        )

    with pytest.raises(ValueError, match="summary is required"):
        recall.add_item(
            tmp_path,
            recall.RecallInput(kind="decision", summary=" "),
        )

    assert not recall.ledger_path(tmp_path).exists()


def test_context_ledger_add_and_recall_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI can add and recall compaction-safe context items."""
    log_dir = tmp_path / ".verify-logs"

    assert (
        cli.main(
            [
                "--log-dir",
                str(log_dir),
                "ledger",
                "add",
                "--kind",
                "decision",
                "--summary",
                "Keep MCP context packs pointer-only",
                "--path",
                "src/agent_maintainer/mcp/tools.py",
                "--artifact",
                ".verify-logs/context/PACK.md",
                "--command",
                "python -m agent_maintainer context recall --kind decision",
                "--tag",
                "mcp",
                "--value",
                "surface=v0",
            ],
        )
        == 0
    )
    added = capsys.readouterr().out
    assert "Recall ledger item added" in added

    assert (
        cli.main(
            [
                "--log-dir",
                str(log_dir),
                "recall",
                "--kind",
                "decision",
                "--query",
                "mcp",
            ],
        )
        == 0
    )
    recalled = capsys.readouterr().out
    assert "Keep MCP context packs pointer-only" in recalled
    assert "src/agent_maintainer/mcp/tools.py" in recalled
    assert "surface=v0" in recalled
