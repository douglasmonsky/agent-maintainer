"""Tests hook runtime event instrumentation."""

from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.hooks import runtime

ENCODING = "utf-8"
SUCCESS_EXIT = 0
EXPECTED_EVENT_FILE_COUNT = 1


class SuccessfulVerifier:
    """Fake successful verifier runner."""

    def __call__(
        self,
        command: list[str],
        _repo_root: Path,
    ) -> subprocess.CompletedProcess[str]:
        """Return a successful verifier result."""
        return subprocess.CompletedProcess(command, SUCCESS_EXIT, "", "")


class RaisingVerifier:
    """Fake verifier runner raising an exception."""

    def __call__(
        self,
        _command: list[str],
        _repo_root: Path,
    ) -> subprocess.CompletedProcess[str]:
        """Raise a fake verifier exception."""
        raise RuntimeError("boom with password=hunter2")


class ForbiddenVerifier:
    """Verifier runner that must not be called."""

    def __call__(
        self,
        _command: list[str],
        _repo_root: Path,
    ) -> subprocess.CompletedProcess[str]:
        """Fail if verification runs."""
        pytest.fail("hook no-op should not run verification")


def test_hook_success_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Configured repositories record successful hook runtime events."""
    runtime_events_installed_repo(tmp_path)
    monkeypatch.setattr(runtime, "run_verifier_bounded", SuccessfulVerifier())

    status = runtime.run_hook(
        platform=runtime.CODEX_PLATFORM,
        event=runtime.POST_TOOL_USE_EVENT,
        profile="fast",
        repo_root=tmp_path,
    )

    assert status == SUCCESS_EXIT
    assert capsys.readouterr().out == ""
    assert_success_records(hook_event_records(tmp_path))


def test_hook_recursive_noop_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Configured recursive stop hooks record no-op runtime events."""
    runtime_events_installed_repo(tmp_path)
    monkeypatch.setattr(sys, "stdin", StringIO('{"stop_hook_active": true}'))
    monkeypatch.setattr(runtime, "run_verifier_bounded", ForbiddenVerifier())

    status = runtime.run_hook(
        platform=runtime.CODEX_PLATFORM,
        event=runtime.STOP_EVENT,
        profile="precommit",
        repo_root=tmp_path,
    )

    assert status == SUCCESS_EXIT
    assert json.loads(capsys.readouterr().out) == {"continue": True}
    assert_recursive_noop_records(hook_event_records(tmp_path))


def test_hook_missing_verifier_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Configured repositories record missing-verifier hook events."""
    runtime_events_repo(tmp_path)
    monkeypatch.setattr(runtime, "package_command_available", package_unavailable)

    status = runtime.run_hook(
        platform=runtime.CLAUDE_CODE_PLATFORM,
        event=runtime.STOP_EVENT,
        profile="precommit",
        repo_root=tmp_path,
    )

    assert status == SUCCESS_EXIT
    assert json.loads(capsys.readouterr().out)["decision"] == "block"
    assert_missing_verifier_records(hook_event_records(tmp_path))


def test_hook_exception_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hook runtime exceptions emit compact sanitized runtime events."""
    runtime_events_installed_repo(tmp_path)
    monkeypatch.setattr(runtime, "run_verifier_bounded", RaisingVerifier())

    with pytest.raises(RuntimeError):
        runtime.run_hook(
            platform=runtime.CODEX_PLATFORM,
            event=runtime.POST_TOOL_USE_EVENT,
            profile="fast",
            repo_root=tmp_path,
        )

    assert_exception_records(hook_event_records(tmp_path))


def runtime_events_repo(tmp_path: Path) -> Path:
    """Create configured repository with runtime events enabled."""
    (tmp_path / "pyproject.toml").write_text(
        """[tool.agent_maintainer]
runtime_events_enabled = true
runtime_events_dir = '.events'
""",
        encoding=ENCODING,
    )
    return tmp_path


def runtime_events_installed_repo(tmp_path: Path) -> Path:
    """Create runtime-event repository with local package entrypoint."""
    runtime_events_repo(tmp_path)
    package_root = tmp_path / "src" / "agent_maintainer"
    package_root.mkdir(parents=True)
    (package_root / "__main__.py").write_text("", encoding=ENCODING)
    return tmp_path


def hook_event_records(repo_root: Path) -> list[dict[str, object]]:
    """Read the single hook runtime event file."""
    event_files = tuple((repo_root / ".events").glob("*.jsonl"))
    assert len(event_files) == EXPECTED_EVENT_FILE_COUNT
    return [json.loads(line) for line in event_files[0].read_text(encoding=ENCODING).splitlines()]


def assert_success_records(records: list[dict[str, object]]) -> None:
    """Assert successful hook event contract."""
    assert event_names(records) == ["hook.invoked", "hook.finished"]
    assert records[0]["hook_id"] == (f"{runtime.CODEX_PLATFORM}:{runtime.POST_TOOL_USE_EVENT}")
    assert records[0]["repo_configured"] is True
    assert records[1]["status"] == "passed"
    assert records[1]["exit_code"] == SUCCESS_EXIT


def assert_recursive_noop_records(records: list[dict[str, object]]) -> None:
    """Assert recursive no-op hook event contract."""
    assert event_names(records) == ["hook.invoked", "hook.finished"]
    assert records[1]["status"] == "recursive_noop"
    assert records[1]["exit_code"] == SUCCESS_EXIT


def assert_missing_verifier_records(records: list[dict[str, object]]) -> None:
    """Assert missing verifier hook event contract."""
    assert event_names(records) == ["hook.invoked", "hook.finished"]
    assert records[1]["status"] == "missing_verifier"
    assert records[1]["hook_id"] == f"{runtime.CLAUDE_CODE_PLATFORM}:{runtime.STOP_EVENT}"


def assert_exception_records(records: list[dict[str, object]]) -> None:
    """Assert exception hook event contract."""
    attributes = cast("dict[str, object]", records[1]["attributes"])
    assert event_names(records) == ["hook.invoked", "hook.exception"]
    assert attributes["exception_type"] == "RuntimeError"
    assert "hunter2" not in str(attributes["message"])


def event_names(records: list[dict[str, object]]) -> list[object]:
    """Return event names from records."""
    return [record["event_name"] for record in records]


def package_unavailable() -> bool:
    """Return unavailable package command for missing-verifier tests."""
    return False
