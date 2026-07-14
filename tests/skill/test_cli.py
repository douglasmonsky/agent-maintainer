"""Tests for personal setup-skill command routing."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_maintainer import cli as root_cli
from agent_maintainer.config import preflight
from agent_maintainer.skill import cli, lifecycle
from agent_maintainer.skill.models import SkillState, SkillStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
ARGUMENT_ERROR = 2


def test_install_forwards_repeatable_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One invocation can install the shared resource for both clients."""
    calls: list[tuple[Path, tuple[str, ...]]] = []
    monkeypatch.setattr(cli, "user_home", lambda: tmp_path)

    def fake_install(home: Path, clients: tuple[str, ...]) -> tuple[SkillStatus, ...]:
        calls.append((home, clients))
        return (_status(tmp_path, "codex", SkillState.CURRENT),)

    monkeypatch.setattr(cli.lifecycle, "install", fake_install)

    result = cli.main(["install", "--client", "codex", "--client", "claude-code"])

    assert result == 0
    assert calls == [(tmp_path, ("codex", "claude-code"))]
    assert "codex: current" in capsys.readouterr().out


def test_status_defaults_to_both_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read-only status covers both supported personal clients by default."""
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(cli, "user_home", lambda: tmp_path)

    def fake_status(home: Path, client: str) -> SkillStatus:
        calls.append((home, client))
        return _status(home, client, SkillState.MISSING)

    monkeypatch.setattr(cli.lifecycle, "status", fake_status)

    assert cli.main(["status"]) == 0
    assert calls == [(tmp_path, "codex"), (tmp_path, "claude-code")]


@pytest.mark.parametrize("command", ("install", "uninstall"))
def test_mutation_requires_client_before_dispatch(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing mutation target is a parser error, never an implicit write."""

    def fail_mutation(_home: Path, _clients: tuple[str, ...]) -> tuple[SkillStatus, ...]:
        pytest.fail("mutation dispatched")

    monkeypatch.setattr(cli.lifecycle, command, fail_mutation)

    with pytest.raises(SystemExit) as raised:
        cli.main([command])

    assert raised.value.code == ARGUMENT_ERROR


def test_ownership_error_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsafe personal state reports one concise error without a traceback."""
    monkeypatch.setattr(cli, "user_home", lambda: tmp_path)

    def raise_ownership(_home: Path, _clients: tuple[str, ...]) -> tuple[SkillStatus, ...]:
        raise lifecycle.SkillOwnershipError("edited file")

    monkeypatch.setattr(cli.lifecycle, "install", raise_ownership)

    assert cli.main(["install", "--client", "codex"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "edited file\n"


@pytest.mark.parametrize("state", tuple(SkillState))
def test_status_rendering_names_every_public_state(
    state: SkillState,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every lifecycle state has stable client-prefixed text output."""
    monkeypatch.setattr(cli, "user_home", lambda: tmp_path)

    def fake_status(home: Path, client: str) -> SkillStatus:
        return _status(home, client, state)

    monkeypatch.setattr(cli.lifecycle, "status", fake_status)

    assert cli.main(["status", "--client", "codex"]) == 0
    assert capsys.readouterr().out.startswith(f"codex: {state.value}")


def test_top_level_skill_route_skips_repository_preflight() -> None:
    """Personal skill management remains available outside configured repositories."""
    handler = root_cli.command_handlers()["skill"]

    assert handler is root_cli.skill_command
    assert not isinstance(handler, preflight.ValidatedCommand)
    assert "skill           Install the setup skill" in root_cli.USAGE


def test_real_status_command_works_outside_git_repository(tmp_path: Path) -> None:
    """The installed command needs only a home directory, not repository config."""
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
    )

    completed = subprocess.run(  # nosec B603: fixed interpreter and module command.
        [sys.executable, "-m", "agent_maintainer", "skill", "status"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "codex: missing" in completed.stdout
    assert "claude-code: missing" in completed.stdout


def _status(home: Path, client: str, state: SkillState) -> SkillStatus:
    return SkillStatus(
        client=client,
        destination=lifecycle.client_destination(home, client),
        state=state,
        package_version="1.2.3",
        installed_version="1.0.0" if state is not SkillState.MISSING else None,
        detail="test detail" if state is SkillState.LOCALLY_MODIFIED else "",
    )
