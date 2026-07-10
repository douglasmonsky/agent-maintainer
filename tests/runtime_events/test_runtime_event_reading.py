"""Tests runtime event JSONL reading."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_context.reading import file_safety
from agent_maintainer.runtime_events.read import (
    DEFAULT_RUNTIME_EVENT_FILE_LIMIT,
    MAX_RUNTIME_EVENT_FILE_BYTES,
    read_runtime_events,
)

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


def test_read_runtime_events_refuses_outside_symlink_canary(tmp_path: Path) -> None:
    """An event symlink cannot disclose a valid outside JSONL canary."""
    repo_root = tmp_path / "repo"
    events_dir = repo_root / "events"
    events_dir.mkdir(parents=True)
    outside = tmp_path / "outside.jsonl"
    outside.write_text(json.dumps({"canary": "outside-secret"}), encoding="utf-8")
    (events_dir / "events.jsonl").symlink_to(outside)

    result = read_runtime_events(events_dir, workspace_root=repo_root)

    assert result.records == []
    assert result.files_read == 0


def test_read_runtime_events_refuses_symlinked_event_directory(tmp_path: Path) -> None:
    """A symlinked event directory is never enumerated as trusted input."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside_dir = tmp_path / "outside-events"
    outside_dir.mkdir()
    (outside_dir / "events.jsonl").write_text(
        json.dumps({"canary": "outside-secret"}),
        encoding="utf-8",
    )
    events_dir = repo_root / "events"
    events_dir.symlink_to(outside_dir, target_is_directory=True)

    result = read_runtime_events(events_dir, workspace_root=repo_root)

    assert result.records == []
    assert result.files_read == 0


def test_read_runtime_events_refuses_fifo_without_blocking(tmp_path: Path) -> None:
    """A JSONL FIFO is rejected before any content read."""
    fifo = tmp_path / "events.jsonl"
    os.mkfifo(fifo)

    result = read_runtime_events(tmp_path)

    assert result.records == []
    assert result.files_read == 0


def test_read_runtime_events_refuses_sparse_oversized_file(tmp_path: Path) -> None:
    """An oversized JSONL file is rejected from metadata before reading."""
    event_file = tmp_path / "events.jsonl"
    event_file.touch()
    os.truncate(event_file, MAX_RUNTIME_EVENT_FILE_BYTES + 1)

    result = read_runtime_events(tmp_path)

    assert result.records == []
    assert result.files_read == 0


def test_read_runtime_events_refuses_non_utf8_file(tmp_path: Path) -> None:
    """Non-UTF-8 JSONL input is skipped without a traceback."""
    (tmp_path / "events.jsonl").write_bytes(b'{"event_name":"bad"}\xff')

    result = read_runtime_events(tmp_path)

    assert result.records == []
    assert result.files_read == 0


def test_read_runtime_events_default_cap_does_not_open_older_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Default aggregate reads open only the newest bounded file set."""
    for index in range(DEFAULT_RUNTIME_EVENT_FILE_LIMIT + 3):
        (tmp_path / f"events-{index:03d}.jsonl").write_text(
            json.dumps({"event_name": f"event.{index}"}),
            encoding="utf-8",
        )
    opened: list[Path] = []
    original = file_safety.read_bounded_utf8_file

    def tracked_read(
        path: Path,
        *,
        workspace_root: Path | None = None,
        max_bytes: int = file_safety.MAX_FILE_BYTES,
    ) -> file_safety.SafeTextRead:
        opened.append(path)
        return original(path, workspace_root=workspace_root, max_bytes=max_bytes)

    monkeypatch.setattr(file_safety, "read_bounded_utf8_file", tracked_read)

    result = read_runtime_events(tmp_path)

    assert result.files_read == DEFAULT_RUNTIME_EVENT_FILE_LIMIT
    assert len(opened) == DEFAULT_RUNTIME_EVENT_FILE_LIMIT
    assert tmp_path / "events-000.jsonl" not in opened
