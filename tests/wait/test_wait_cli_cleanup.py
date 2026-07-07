"""Tests wait cleanup CLI behavior."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from agent_maintainer.wait import cli
from agent_maintainer.wait.registry import RESULT_PASS, RegisterWait, WaitRegistry

NOW = datetime.fromisoformat("2026-07-07T02:00:00+00:00")


def test_cleanup_cli_expires_stale_ready_text(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cleanup CLI prints a compact text summary."""

    register_ready_wait(tmp_path)

    status = cli.main(
        [
            "cleanup",
            "--root",
            str(tmp_path),
            "--ready-older-than-seconds",
            "0",
        ],
    )

    assert status == 0
    assert capsys.readouterr().out == "expired ready waits: 1\n"


def test_cleanup_cli_expires_stale_ready_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cleanup CLI supports parseable JSON output."""

    register_ready_wait(tmp_path)

    status = cli.main(
        [
            "cleanup",
            "--root",
            str(tmp_path),
            "--ready-older-than-seconds",
            "0",
            "--format",
            "json",
        ],
    )

    assert status == 0
    assert json.loads(capsys.readouterr().out) == {"expired_ready": 1}


def register_ready_wait(root: Path) -> None:
    """Create one ready wait record for cleanup tests."""

    registry = WaitRegistry(root)
    record = registry.register(
        RegisterWait(root=root, kind="verifier", target_id="run-123", now=NOW),
    )
    registry.complete(
        record,
        terminal_result=RESULT_PASS,
        resume_message="done",
        state_data={"ok": True},
        now=NOW,
    )
