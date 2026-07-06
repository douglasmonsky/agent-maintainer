"""Tests for attention ledger building."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.attention import builder, signals

TRACKED_FILE_CAP_TEST_TOTAL = 5
TRACKED_FILE_CAP_TEST_LIMIT = 2


def test_attention_ledger_is_deterministic_with_missing_inputs(tmp_path: Path) -> None:
    """Missing optional artifacts still produce deterministic JSON."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")

    first = builder.build_attention_ledger(tmp_path).to_payload()
    second = builder.build_attention_ledger(tmp_path).to_payload()

    assert first == second
    assert first["schema_version"] == 1
    assert isinstance(first["files"], list)
    paths = {item["path"] for item in first["files"]}
    assert {"README.md", "src/app.py"} <= paths


def test_attention_ledger_scores_artifact_and_change_signals(tmp_path: Path) -> None:
    """Builder combines git, runtime, verifier, DocSync, and baseline signals."""
    _init_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_app.py", "def test_app():\n    assert True\n")
    _write(tmp_path / "README.md", "# Example\n")
    _write(tmp_path / "docs" / "guide.md", "# Guide\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    _write(tmp_path / "src" / "app.py", "VALUE = 2\n")
    _write(
        tmp_path / ".verify-logs" / "events" / "events.jsonl",
        json.dumps({"event_name": "agent.file", "attributes": {"path": "src/app.py"}}) + "\n",
    )
    _write(
        tmp_path / ".verify-logs" / "runs" / "run-1" / "manifest.json",
        json.dumps({"checks": [{"summary": "failure in tests/test_app.py"}]}),
    )
    _write(tmp_path / ".docsync" / "trace.yml", "claim: README.md\n")
    _write(
        tmp_path / ".verify-logs" / "file-baselines.json",
        json.dumps({"findings": [{"path": "docs/guide.md"}]}),
    )

    ledger = builder.build_attention_ledger(tmp_path)
    by_path = {score.path: score for score in ledger.files}

    assert by_path["src/app.py"].components["git_changed"] == 1.0
    assert by_path["src/app.py"].components["runtime_events"] == 1.0
    assert by_path["tests/test_app.py"].components["verifier_artifacts"] == 1.0
    assert by_path["README.md"].components["docsync"] == 1.0
    assert by_path["docs/guide.md"].components["file_baselines"] == 1.0
    assert by_path["src/app.py"].score > by_path["docs/guide.md"].score


def test_attention_ledger_scores_untracked_repo_files(tmp_path: Path) -> None:
    """New untracked source files are still attention targets during active edits."""
    _init_repo(tmp_path)
    _write(tmp_path / "README.md", "# Example\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    _write(tmp_path / "src" / "new_module.py", "VALUE = 1\n")

    ledger = builder.build_attention_ledger(tmp_path)
    by_path = {score.path: score for score in ledger.files}

    assert by_path["src/new_module.py"].components["git_changed"] == 1.0


def test_attention_ledger_collects_tracked_files_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Builder shares one tracked-file collection with signal readers."""

    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    _write(
        tmp_path / ".docsync" / "trace.yml",
        "documents:\n  app:\n    path: src/app.py\n",
    )
    calls = 0
    original = signals.tracked_files

    def counted_tracked_files(repo_root: Path) -> tuple[str, ...]:
        nonlocal calls
        calls += 1
        return original(repo_root)

    monkeypatch.setattr(signals, "tracked_files", counted_tracked_files)

    ledger = builder.build_attention_ledger(tmp_path)

    assert calls == 1
    assert ledger.inputs["docsync_files"] == 1


def test_attention_ledger_reports_tracked_file_cap(tmp_path: Path) -> None:
    """Large repositories use deterministic cap and report guard note."""

    for index in range(TRACKED_FILE_CAP_TEST_TOTAL):
        _write(tmp_path / "src" / f"file_{index}.py", f"VALUE = {index}\n")

    ledger = builder.build_attention_ledger(
        tmp_path,
        max_tracked_files=TRACKED_FILE_CAP_TEST_LIMIT,
    )
    guards = cast(dict[str, object], ledger.inputs["performance_guards"])

    assert guards["all_tracked_file_count"] == TRACKED_FILE_CAP_TEST_TOTAL
    assert guards["scored_file_count"] == TRACKED_FILE_CAP_TEST_LIMIT
    assert guards["notes"] == ["tracked file set capped 2/5 using deterministic sampling"]


def _init_repo(path: Path) -> None:
    """Initialize a minimal git repository for signal tests."""
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test User")


def _git(path: Path, *args: str) -> None:
    """Run git in a test repository."""
    subprocess.run(("git", *args), cwd=path, check=True, capture_output=True, text=True)


def _write(path: Path, content: str) -> None:
    """Write a file, creating parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
