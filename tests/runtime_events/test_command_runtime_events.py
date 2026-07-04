"""Tests command-level runtime event instrumentation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer import cli
from agent_maintainer.runtime_events.commands import resolve_command_name

ENCODING = "utf-8"
SUCCESS_EXIT = 0
FAIL_EXIT = 2


def test_known_command_success_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured repositories record compact command success events."""

    runtime_events_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "command_handlers", fake_handlers)

    status = cli.main(["fake", "--token", "sk-secret-value-that-should-not-appear"])

    records = event_records(tmp_path)
    assert status == SUCCESS_EXIT
    assert_success_records(records)
    serialized = json.dumps(records)
    assert "sk-secret-value-that-should-not-appear" not in serialized
    assert "--token" not in serialized


def test_unknown_command_uses_safe_command_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unknown commands emit safe metadata without raw command text."""

    runtime_events_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "command_handlers", fake_handlers)

    status = cli.main(["secret-command-value", "--password=hunter2"])

    records = event_records(tmp_path)
    assert status == FAIL_EXIT
    assert "Unknown maintainer command" in capsys.readouterr().err
    assert_unknown_records(records)
    serialized = json.dumps(records)
    assert "secret-command-value" not in serialized
    assert "hunter2" not in serialized


def test_command_exception_event_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Command exceptions emit compact sanitized failure events."""

    runtime_events_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "command_handlers", raising_handlers)

    with pytest.raises(RuntimeError, match="boom"):
        cli.main(["fake"])

    records = event_records(tmp_path)
    assert [record["event_name"] for record in records] == [
        "command.started",
        "command.exception",
    ]
    assert records[1]["severity"] == "error"
    assert records[1]["status"] == "exception"
    attributes = event_attributes(records[1])
    assert attributes["exception_type"] == "RuntimeError"
    assert "password=[redacted]" in attributes["exception_message"]


def test_command_events_disabled_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default configuration does not create command event files."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "command_handlers", fake_handlers)

    assert cli.main(["fake"]) == SUCCESS_EXIT
    assert not list(tmp_path.glob(".verify-logs/events/*.jsonl"))


def test_resolve_command_name_omits_raw_unknowns() -> None:
    """Safe command resolver only returns known commands or coarse labels."""

    assert resolve_command_name([], {"verify"}) == "help"
    assert resolve_command_name(["--help"], {"verify"}) == "help"
    assert resolve_command_name(["verify"], {"verify"}) == "verify"
    assert resolve_command_name(["sk-secret-value"], {"verify"}) == "unknown"


def runtime_events_repo(tmp_path: Path) -> Path:
    """Create a configured repo with runtime events enabled."""

    (tmp_path / "pyproject.toml").write_text(
        """[tool.agent_maintainer]
runtime_events_enabled = true
runtime_events_dir = ".events"
""",
        encoding=ENCODING,
    )
    return tmp_path


def fake_handlers() -> dict[str, cli.CommandRunner]:
    """Return safe fake command handlers for CLI runtime event tests."""

    return {"fake": lambda _args: SUCCESS_EXIT}


def raising_handlers() -> dict[str, cli.CommandRunner]:
    """Return fake command handler that raises a sensitive-message exception."""

    return {"fake": raise_error}


def raise_error(_args: list[str]) -> int:
    """Raise fake sensitive-message command exception."""

    raise RuntimeError("boom password=hunter2")


def assert_success_records(records: list[dict[str, object]]) -> None:
    """Assert successful command runtime event contract."""

    assert [record["event_name"] for record in records] == [
        "command.started",
        "command.finished",
    ]
    assert records[0]["command"] == "fake"
    assert records[1]["status"] == "pass"
    assert records[1]["exit_code"] == SUCCESS_EXIT


def assert_unknown_records(records: list[dict[str, object]]) -> None:
    """Assert unknown command runtime event contract."""

    assert [record["command"] for record in records] == ["unknown", "unknown"]
    assert records[1]["status"] == "fail"


def event_attributes(record: dict[str, object]) -> dict[str, str]:
    """Return typed event attributes from a runtime event record."""

    return cast("dict[str, str]", record["attributes"])


def event_records(tmp_path: Path) -> list[dict[str, object]]:
    """Return emitted JSONL event records."""

    event_files = list((tmp_path / ".events").glob("*.jsonl"))
    assert len(event_files) == 1
    return [json.loads(line) for line in event_files[0].read_text(encoding=ENCODING).splitlines()]
