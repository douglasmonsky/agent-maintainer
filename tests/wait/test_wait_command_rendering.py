"""Tests shell rendering for durable wait commands."""

from __future__ import annotations

import json
import shlex
import sys
from datetime import datetime
from pathlib import Path

import pytest

from agent_waits import registry as wait_registry
from agent_waits.broker import heartbeat_request_json
from agent_waits.registry import RegisterWait, WaitRegistry

NOW = datetime.fromisoformat("2026-07-07T02:00:00+00:00")


def test_default_wait_commands_use_the_running_executable_and_quote_root(
    tmp_path: Path,
) -> None:
    """Default monitor commands remain runnable from roots with spaces."""

    root = tmp_path / "repo root"
    record = WaitRegistry(root).register(
        RegisterWait(root=root, kind="verifier", target_id="run-123", now=NOW),
    )

    request = json.loads(heartbeat_request_json(record, root=root))
    executable = shlex.quote(sys.executable)
    quoted_root = shlex.quote(str(root))
    resume = f"{executable} -m agent_maintainer wait resume {record.wait_id}"

    assert record.resume_instruction == resume
    assert request["sweep_command"] == (
        f"{executable} -m agent_maintainer wait sweep --one {record.wait_id} --root {quoted_root}"
    )
    assert request["resume_command"] == f"{resume} --root {quoted_root}"


def _forged_wait_id(_kind: str, _target_id: str, _created_at: str) -> str:
    """Return an intentionally shell-sensitive wait identifier."""

    return "wait-123; touch compromised"


def test_default_wait_commands_quote_forged_wait_identifiers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default shell commands treat an untrusted wait ID as one token."""

    monkeypatch.setattr(wait_registry, "_wait_id", _forged_wait_id)
    record = WaitRegistry(tmp_path).register(
        RegisterWait(root=tmp_path, kind="verifier", target_id="run-123", now=NOW),
    )

    request = json.loads(heartbeat_request_json(record))
    quoted_id = shlex.quote(record.wait_id)
    executable = shlex.quote(sys.executable)

    assert record.resume_instruction == (
        f"{executable} -m agent_maintainer wait resume {quoted_id}"
    )
    assert request["sweep_command"] == (
        f"{executable} -m agent_maintainer wait sweep --one {quoted_id}"
    )
