"""Tests for attention signal extraction."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.attention import signals


def test_payload_paths_extracts_nested_known_paths(tmp_path: Path) -> None:
    """Nested JSON payloads mention known repo paths deterministically."""
    known = {"src/app.py", "tests/test_app.py"}
    payload = {
        "checks": [
            {"summary": "failure in tests/test_app.py"},
            {"attributes": {"path": "src/app.py"}},
        ]
    }

    paths = signals._payload_paths(payload, repo_root=tmp_path, known_paths=known)

    assert paths == {"src/app.py", "tests/test_app.py"}


def test_runtime_event_counts_reads_jsonl_paths(tmp_path: Path) -> None:
    """Runtime event signal extraction counts file path mentions."""
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(
        tmp_path / ".verify-logs" / "events" / "events.jsonl",
        json.dumps({"event_name": "agent.file", "attributes": {"path": "src/app.py"}}) + "\n",
    )

    counts = signals.runtime_event_counts(
        tmp_path,
        events_dir=tmp_path / ".verify-logs" / "events",
    )

    assert counts["src/app.py"] == 1


def _write(path: Path, content: str) -> None:
    """Write a file, creating parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
