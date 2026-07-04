"""Tests runtime event JSONL reading."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.runtime_events.read import read_runtime_events

LIMITED_FILE_COUNT = 2
TOTAL_FILE_COUNT = 3


def test_read_runtime_events_handles_missing_dir(tmp_path: Path) -> None:
    """Missing event directories produce empty result."""
    result = read_runtime_events(tmp_path / "missing")

    assert result.files_read == 0
    assert result.records == []
    assert result.malformed_lines == 0


def test_read_runtime_events_counts_bad_lines(tmp_path: Path) -> None:
    """Reader keeps valid objects and counts invalid JSONL lines."""
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(
        "\n".join((json.dumps({"event_name": "command.started"}), "bad")),
        encoding="utf-8",
    )

    result = read_runtime_events(tmp_path)

    assert result.files_read == 1
    assert [record["event_name"] for record in result.records] == ["command.started"]
    assert result.malformed_lines == 1


def test_read_runtime_events_applies_file_limit(tmp_path: Path) -> None:
    """Reader limits oldest files before parsing."""
    for index in range(TOTAL_FILE_COUNT):
        event_file = tmp_path / f"events-{index}.jsonl"
        payload = {"event_name": f"event.{index}"}
        event_file.write_text(
            f"{json.dumps(payload)}\n",
            encoding="utf-8",
        )

    result = read_runtime_events(tmp_path, file_limit=LIMITED_FILE_COUNT)

    assert result.files_read == LIMITED_FILE_COUNT
    assert [record["event_name"] for record in result.records] == [
        "event.1",
        "event.2",
    ]
