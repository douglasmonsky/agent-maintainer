"""Tests the root fail-closed configuration boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer import cli
from agent_maintainer.config import preflight

CONFIGURATION_ERROR_STATUS = 2
SUCCESS_STATUS = 0


def write_invalid_fresh_strict_config(repo_root: Path) -> None:
    """Write policy whose explicit warning threshold exceeds its mode block."""

    (repo_root / "pyproject.toml").write_text(
        """[tool.agent_maintainer]
mode = "fresh-strict"
change_warn_lines = 700
""",
        encoding="utf-8",
    )


def test_invalid_fresh_strict_stops_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A real root command cannot continue after contradictory policy."""

    calls: list[list[str]] = []
    write_invalid_fresh_strict_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "command_handlers", lambda: fake_handlers(calls))

    status = cli.main(["fake"])

    assert status == CONFIGURATION_ERROR_STATUS
    assert calls == []
    assert_config_failure(capsys.readouterr().err, tmp_path)


def test_subcommand_help_bypasses_invalid_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Help remains reachable when users need to repair invalid policy."""

    calls: list[list[str]] = []
    write_invalid_fresh_strict_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "command_handlers", lambda: fake_handlers(calls))

    assert cli.main(["fake", "--help"]) == SUCCESS_STATUS
    assert calls == [["--help"]]


def test_malformed_shell_env_stops_root_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Loader parse failures stay typed through the root preflight boundary."""

    calls: list[list[str]] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_MAINTAINER_PIP_AUDIT_ARGS", "'unterminated")
    monkeypatch.setattr(cli, "command_handlers", lambda: fake_handlers(calls))

    assert cli.main(["fake"]) == CONFIGURATION_ERROR_STATUS
    assert calls == []
    error = capsys.readouterr().err
    assert "AGENT_MAINTAINER_PIP_AUDIT_ARGS" in error
    assert "invalid shell syntax" in error


def test_unknown_command_ignores_invalid_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unknown-command handling does not get hidden by repository policy."""

    write_invalid_fresh_strict_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert cli.main(["unknown-private-value"]) == CONFIGURATION_ERROR_STATUS
    error = capsys.readouterr().err
    assert "Unknown maintainer command" in error
    assert "FAIL configuration" not in error


def test_repository_root_handlers_have_config_preflight() -> None:
    """Only the personal skill command may bypass repository validation."""

    handlers = cli.command_handlers()
    validated = {
        name: handler
        for name, handler in handlers.items()
        if isinstance(handler, preflight.ValidatedCommand)
    }

    assert handlers
    assert set(handlers) - set(validated) == {"skill"}
    assert handlers["skill"] is cli.skill_command
    assert all(handler.original_handler() for handler in validated.values())


def fake_handlers(calls: list[list[str]]) -> dict[str, cli.CommandRunner]:
    """Return one observable command handler."""

    return {
        "fake": preflight.ValidatedCommand(
            lambda arguments: calls.append(arguments) or SUCCESS_STATUS,
        )
    }


def assert_config_failure(error: str, repo_root: Path) -> None:
    """Assert compact migration-quality root diagnostics."""

    assert "FAIL configuration" in error
    assert str(repo_root / "pyproject.toml") in error
    assert "change_block_lines" in error
