"""Tests shell rendering for durable wait commands."""

from __future__ import annotations

import json
import os
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default monitor commands remain runnable from roots with spaces."""

    monkeypatch.delenv("PYTHONPATH", raising=False)
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

    monkeypatch.delenv("PYTHONPATH", raising=False)
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


def test_source_checkout_commands_prefix_resolved_pythonpath(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source-layout commands preserve a root-resolved import path."""

    root = tmp_path / "repo root"
    monkeypatch.setenv("PYTHONPATH", "src")
    record = WaitRegistry(root).register(
        RegisterWait(root=root, kind="verifier", target_id="run-123", now=NOW),
    )

    request = json.loads(heartbeat_request_json(record, root=root))
    prefix = f"PYTHONPATH={shlex.quote(str(root / 'src'))} "
    executable = shlex.quote(sys.executable)

    assert record.resume_instruction == (
        f"{prefix}{executable} -m agent_maintainer wait resume {record.wait_id}"
    )
    assert request["sweep_command"] == (
        f"{prefix}{executable} -m agent_maintainer wait sweep --one {record.wait_id} "
        f"--root {shlex.quote(str(root))}"
    )


def test_source_checkout_commands_resolve_pythonpath_lists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Relative and empty Python path entries resolve against the wait root."""

    root = tmp_path / "repo root"
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(("src", "", "vendor")))
    record = WaitRegistry(root).register(
        RegisterWait(root=root, kind="verifier", target_id="run-123", now=NOW),
    )

    request = json.loads(heartbeat_request_json(record, root=root))
    resolved = os.pathsep.join(
        str(root / entry) if entry else str(root) for entry in ("src", "", "vendor")
    )
    prefix = f"PYTHONPATH={shlex.quote(resolved)} "

    assert record.resume_instruction.startswith(prefix)
    assert request["sweep_command"].startswith(prefix)
