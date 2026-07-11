"""Tests for attention signal extraction."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_context.reading import file_safety
from agent_maintainer.attention import signal_context, signals


def test_payload_paths_extracts_nested_known_paths(tmp_path: Path) -> None:
    """Nested JSON payloads mention known repo paths deterministically."""
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(tmp_path / "src" / "ignored.py", "VALUE = 2\n")
    _write(tmp_path / "tests" / "test_app.py", "def test_app(): pass\n")
    payload = {
        "event_name": "agent.check",
        "checks": [
            {"summary": "failure in tests/test_app.py"},
            {"attributes": {"path": "src/app.py"}},
        ],
    }
    events_dir = tmp_path / ".verify-logs" / "events"
    _write(events_dir / "events.jsonl", f"{json.dumps(payload)}\n")

    counts = signals.runtime_event_counts(tmp_path, events_dir=events_dir)

    assert counts == {"src/app.py": 1, "tests/test_app.py": 1}


def test_tracked_file_provider_applies_discovery_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracked and untracked Git outputs are capped before context sampling."""

    monkeypatch.setattr(signals, "DEFAULT_TRACKED_DISCOVERY_LIMIT", 3)

    def git_lines(_repo_root: Path, args: tuple[str, ...]) -> tuple[str, ...]:
        return ("a.py", "b.py", "c.py") if "--others" not in args else ("d.py", "e.py", "f.py")

    monkeypatch.setattr(
        signals,
        "_git_lines",
        git_lines,
    )

    assert signals.tracked_files(tmp_path) == ("a.py", "b.py", "c.py")


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


def test_docsync_counts_refuses_oversized_artifact(tmp_path: Path) -> None:
    """DocSync artifacts over the byte ceiling are refused, not truncated."""

    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(
        tmp_path / ".docsync" / "trace.yml",
        "src/app.py\n" + ("x" * 100),
    )
    context = signal_context.AttentionSignalContext.build(
        tmp_path,
        tracked_files=signals.tracked_files,
        artifact_read_limit_bytes=12,
    )

    counts = signals.docsync_counts(tmp_path, context=context)

    assert counts == {}
    assert context.performance_notes == [
        "artifact refused trace.yml: file exceeds 12 byte limit",
    ]


def test_runtime_event_counts_refuses_outside_event_directory(tmp_path: Path) -> None:
    """Attention cannot read runtime events outside its repository root."""
    repo_root = tmp_path / "repo"
    _write(repo_root / "src" / "app.py", "VALUE = 1\n")
    outside = tmp_path / "outside-events"
    _write(
        outside / "events.jsonl",
        json.dumps({"attributes": {"path": "src/app.py"}}),
    )

    counts = signals.runtime_event_counts(repo_root, events_dir=outside)

    assert counts == {}


def test_verifier_artifacts_refuse_outside_and_symlinked_runs(tmp_path: Path) -> None:
    """Manifest discovery neither escapes the repository nor follows run symlinks."""
    repo_root = tmp_path / "repo"
    _write(repo_root / "src" / "app.py", "VALUE = 1\n")
    outside_log = tmp_path / "outside-log"
    outside_run = outside_log / "runs" / "run-1"
    _write(
        outside_run / "manifest.json",
        json.dumps({"checks": [{"path": "src/app.py"}]}),
    )

    outside_counts = signals.verifier_artifact_counts(repo_root, log_dir=outside_log)
    linked_run = repo_root / ".verify-logs" / "runs" / "run-1"
    linked_run.parent.mkdir(parents=True)
    linked_run.symlink_to(outside_run, target_is_directory=True)
    linked_counts = signals.verifier_artifact_counts(
        repo_root,
        log_dir=repo_root / ".verify-logs",
    )

    assert outside_counts == {}
    assert linked_counts == {}


def test_verifier_artifacts_refuse_fifo_and_oversized_manifest(tmp_path: Path) -> None:
    """Special and oversized manifests are skipped before content reads."""
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    fifo = tmp_path / ".verify-logs" / "runs" / "fifo" / "manifest.json"
    fifo.parent.mkdir(parents=True)
    os.mkfifo(fifo)
    oversized = tmp_path / ".verify-logs" / "runs" / "large" / "manifest.json"
    _write(
        oversized,
        json.dumps({"checks": [{"path": "src/app.py", "detail": "x" * 100}]}),
    )
    context = signal_context.AttentionSignalContext.build(
        tmp_path,
        tracked_files=signals.tracked_files,
        artifact_read_limit_bytes=32,
    )

    counts = signals.verifier_artifact_counts(
        tmp_path,
        log_dir=tmp_path / ".verify-logs",
        context=context,
    )

    assert counts == {}
    assert context.performance_notes == [
        "artifact refused manifest.json: file exceeds 32 byte limit",
    ]


def test_verifier_artifacts_refuse_non_utf8_and_sensitive_paths(tmp_path: Path) -> None:
    """Invalid encodings and sensitive directory names fail closed."""
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    manifest = tmp_path / ".verify-logs" / "runs" / "run-1" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b"{\xff}")
    sensitive_manifest = tmp_path / ".ssh" / "runs" / "run-1" / "manifest.json"
    _write(
        sensitive_manifest,
        json.dumps({"checks": [{"path": "src/app.py"}]}),
    )

    invalid_counts = signals.verifier_artifact_counts(
        tmp_path,
        log_dir=tmp_path / ".verify-logs",
    )
    sensitive_counts = signals.verifier_artifact_counts(
        tmp_path,
        log_dir=tmp_path / ".ssh",
    )

    assert invalid_counts == {}
    assert sensitive_counts == {}


def test_verifier_artifact_default_cap_does_not_open_older_manifests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Manifest aggregation opens only the newest bounded run set."""
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    manifests: list[Path] = []
    for index in range(signals.DEFAULT_SIGNAL_ARTIFACT_FILE_LIMIT + 3):
        manifest = tmp_path / ".verify-logs" / "runs" / f"run-{index:03d}" / "manifest.json"
        _write(manifest, json.dumps({"checks": [{"path": "src/app.py"}]}))
        manifests.append(manifest)
    for manifest in manifests:
        os.utime(manifest.parent, ns=(1, 1))
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

    counts = signals.verifier_artifact_counts(
        tmp_path,
        log_dir=tmp_path / ".verify-logs",
    )

    assert counts["src/app.py"] == signals.DEFAULT_SIGNAL_ARTIFACT_FILE_LIMIT
    assert len(opened) == signals.DEFAULT_SIGNAL_ARTIFACT_FILE_LIMIT
    assert manifests[0] not in opened


def _write(path: Path, content: str) -> None:
    """Write a file, creating parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
