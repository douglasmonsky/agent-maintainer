"""Tests verifier background wait registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.verify import background_wait
from tests.support.callbacks import constant_callback


def test_register_background_verifier_wait_writes_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifier background launch writes a generic wait record."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        background_wait,
        "start_wait_watcher",
        constant_callback((True, "")),
    )

    registration = background_wait.register_background_verifier_wait(
        "run-123",
        Path(".verify-logs"),
    )

    payload = json.loads(
        (tmp_path / ".verify-logs" / "waits" / f"{registration.record.wait_id}.json").read_text(
            encoding="utf-8"
        ),
    )
    assert registration.watcher_started is True
    assert payload["kind"] == "verifier"
    assert payload["target_id"] == "run-123"
    assert payload["metadata"]["log_dir"] == ".verify-logs"


def test_start_wait_watcher_uses_quiet_sweep_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifier background watcher uses the repo sweep command silently."""

    popen_spy = PopenSpy()
    monkeypatch.setattr(background_wait.subprocess, "Popen", popen_spy)

    started, error = background_wait.start_wait_watcher(tmp_path, "wait-1")

    assert started is True
    assert error == ""
    assert popen_spy.calls[0]["cwd"] == tmp_path
    assert popen_spy.calls[0]["stdin"] == background_wait.subprocess.DEVNULL
    assert popen_spy.calls[0]["stdout"] == background_wait.subprocess.DEVNULL
    assert popen_spy.calls[0]["stderr"] == background_wait.subprocess.DEVNULL
    assert popen_spy.calls[0]["close_fds"] is True
    assert popen_spy.calls[0]["start_new_session"] is True
    command = cast("list[str]", popen_spy.calls[0]["command"])
    assert "--watch" in command


class PopenSpy:
    """Callable recording detached watcher launches."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> object:
        self.calls.append({"command": command, **kwargs})
        return object()
