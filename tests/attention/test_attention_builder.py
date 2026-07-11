"""Tests for attention ledger building."""

from __future__ import annotations

import json
import os
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


def test_read_attention_ledger_round_trips_inside_repository(tmp_path: Path) -> None:
    """A regular bounded ledger inside its repository remains readable."""
    _write(tmp_path / "src" / "app.py", "VALUE = 1\n")
    ledger = builder.build_attention_ledger(tmp_path)
    ledger_path = builder.write_attention_ledger(
        ledger,
        tmp_path / ".verify-logs" / "attention" / "files.json",
    )

    loaded = builder.read_attention_ledger(ledger_path, workspace_root=tmp_path)

    assert loaded == ledger


def test_read_attention_ledger_refuses_outside_canary(tmp_path: Path) -> None:
    """A caller cannot select a valid ledger outside the repository root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside.json"
    _write(outside, json.dumps(_ledger_payload(target="outside-secret")))

    loaded = builder.read_attention_ledger(outside, workspace_root=repo_root)

    assert loaded is None


def test_read_attention_ledger_refuses_symlink_leaf(tmp_path: Path) -> None:
    """An in-repository ledger symlink cannot expose an outside canary."""
    repo_root = tmp_path / "repo"
    ledger_path = repo_root / ".verify-logs" / "attention" / "files.json"
    ledger_path.parent.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    _write(outside, json.dumps(_ledger_payload(target="outside-secret")))
    ledger_path.symlink_to(outside)

    loaded = builder.read_attention_ledger(ledger_path, workspace_root=repo_root)

    assert loaded is None


def test_read_attention_ledger_refuses_fifo_without_blocking(tmp_path: Path) -> None:
    """A FIFO ledger is rejected before opening its content stream."""
    ledger_path = tmp_path / "files.json"
    os.mkfifo(ledger_path)

    loaded = builder.read_attention_ledger(ledger_path, workspace_root=tmp_path)

    assert loaded is None


def test_read_attention_ledger_refuses_oversized_and_non_utf8_files(tmp_path: Path) -> None:
    """Oversized and non-UTF-8 ledgers fail closed without tracebacks."""
    oversized = tmp_path / "oversized.json"
    _write(oversized, json.dumps(_ledger_payload(target="x")))
    non_utf8 = tmp_path / "non-utf8.json"
    non_utf8.write_bytes(b"{\xff}")

    assert (
        builder.read_attention_ledger(
            oversized,
            workspace_root=tmp_path,
            max_bytes=8,
        )
        is None
    )
    assert builder.read_attention_ledger(non_utf8, workspace_root=tmp_path) is None


@pytest.mark.parametrize(
    "invalid_case",
    (
        "schema_version",
        "file_count",
        "path",
        "score",
        "component",
        "reason",
    ),
)
def test_read_attention_ledger_rejects_invalid_contract_fields(
    invalid_case: str,
    tmp_path: Path,
) -> None:
    """Ledger schema, counts, paths, scores, and reasons fail closed."""

    file_payload: dict[str, object] = {
        "path": "src/app.py",
        "score": 0.5,
        "components": {"git_changed": 0.5},
        "reasons": ["src/app.py: changed"],
    }
    payload = _ledger_payload(target=str(tmp_path))
    payload["file_count"] = 1
    payload["files"] = [file_payload]
    if invalid_case == "schema_version":
        payload["schema_version"] = 2
    elif invalid_case == "file_count":
        payload["file_count"] = 0
    elif invalid_case == "path":
        file_payload["path"] = "../secret"
    elif invalid_case == "score":
        file_payload["score"] = float("nan")
    elif invalid_case == "component":
        file_payload["components"] = {"git_changed": 1.1}
    elif invalid_case == "reason":
        file_payload["reasons"] = [1]

    ledger_path = tmp_path / ".verify-logs" / "attention" / "files.json"
    _write(ledger_path, json.dumps(payload))

    assert builder.read_attention_ledger(ledger_path, workspace_root=tmp_path) is None


@pytest.mark.parametrize(
    "invalid_case",
    ("schema_type", "duplicate_path", "top_level", "files_type", "score_type"),
)
def test_read_attention_ledger_rejects_invalid_collection_shapes(
    invalid_case: str,
    tmp_path: Path,
) -> None:
    """Collection shapes, duplicate paths, and boolean numbers fail closed."""

    file_payload: dict[str, object] = {
        "path": "src/app.py",
        "score": 0.5,
        "components": {"git_changed": 0.5},
        "reasons": ["src/app.py: changed"],
    }
    payload = _ledger_payload(target=str(tmp_path))
    payload["file_count"] = 1
    payload["files"] = [file_payload]
    serialized_payload: object = payload
    if invalid_case == "schema_type":
        payload["schema_version"] = True
    elif invalid_case == "duplicate_path":
        payload["file_count"] = 2
        payload["files"] = [file_payload, dict(file_payload)]
    elif invalid_case == "top_level":
        serialized_payload = []
    elif invalid_case == "files_type":
        payload["files"] = "invalid"
    elif invalid_case == "score_type":
        file_payload["score"] = True

    ledger_path = tmp_path / ".verify-logs" / "attention" / "files.json"
    _write(ledger_path, json.dumps(serialized_payload))

    assert builder.read_attention_ledger(ledger_path, workspace_root=tmp_path) is None


def _ledger_payload(*, target: str) -> dict[str, object]:
    """Return one minimal valid attention ledger payload."""
    return {
        "schema_version": 1,
        "target": target,
        "file_count": 0,
        "inputs": {},
        "files": [],
    }


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
