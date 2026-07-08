"""Tests wait CLI background registration behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.wait import cli
from agent_maintainer.wait.github import GitHubRunState, GitHubWaitResult
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import (
    RegisterGitHubPrWait,
    RegisterGitHubRunWait,
    RegisterVerifierWait,
    WaitRegistry,
)
from agent_maintainer.wait.sweeper import sweep_once
from agent_maintainer.wait.verifier import VerifierManifest, VerifierWaitResult

PR_NUMBER = "291"


def test_codex_pr_cli_backgrounds_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground PR waits convert into background registrations."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.start_wait_watcher",
        lambda root, wait_id: calls.append((root, wait_id)),
    )

    status = cli.main(
        [
            "github-pr",
            PR_NUMBER,
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "Result: PENDING" in output
    assert "manual resume:" in output
    assert "heartbeat request:" in output
    assert '"type": "codex_heartbeat_wait"' in output
    assert len(calls) == 1


def test_codex_github_run_cli_backgrounds_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground GitHub run waits convert into background registrations."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.start_wait_watcher",
        lambda root, wait_id: calls.append((root, wait_id)),
    )

    status = cli.main(
        [
            "github-run",
            "123",
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "Result: PENDING" in output
    assert "github-run wait registered" in output
    assert '"wait_kind": "github-run"' in output
    assert calls and calls[0][0] == tmp_path


def test_codex_verifier_cli_backgrounds_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex foreground verifier waits convert into background registrations."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.delenv("AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT", raising=False)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.start_wait_watcher",
        lambda root, wait_id: calls.append((root, wait_id)),
    )

    status = cli.main(
        [
            "verifier",
            "run-1",
            "--root",
            str(tmp_path),
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ],
    )

    output = capsys.readouterr().out
    assert_success(status)
    assert "Result: PENDING" in output
    assert "verifier wait registered" in output
    assert '"wait_kind": "verifier"' in output
    assert calls and calls[0][0] == tmp_path


def test_register_github_pr_cli_writes_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait register CLI persists PR waits and renders JSON."""

    status = cli.main(
        [
            "register",
            "github-pr",
            PR_NUMBER,
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--platform",
            "codex",
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )

    payload = json.loads(capsys.readouterr().out)
    expected_fields = {
        "kind": "github-pr",
        "status": "pending",
        "pr_number": PR_NUMBER,
        "repo": "douglasmonsky/agent-maintainer",
        "platform": "codex",
    }
    assert status == 0
    assert {field: payload[field] for field in expected_fields} == expected_fields
    assert "wait resume" in payload["resume_instruction"]
    assert (tmp_path / ".verify-logs" / "waits" / f"{payload['wait_id']}.json").exists()


def test_register_github_run_cli_writes_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait register CLI persists GitHub run waits."""

    status = cli.main(
        [
            "register",
            "github-run",
            "123",
            "--repo",
            "douglasmonsky/agent-maintainer",
            "--root",
            str(tmp_path),
            "--format",
            "json",
        ],
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["kind"] == "github-run"
    assert payload["target_id"] == "123"
    assert payload["repo"] == "douglasmonsky/agent-maintainer"
    assert "wait resume" in payload["resume_instruction"]


def test_register_verifier_cli_writes_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait register CLI persists verifier waits."""

    status = cli.main(
        [
            "register",
            "verifier",
            "run-1",
            "--root",
            str(tmp_path),
            "--log-dir",
            ".custom-logs",
            "--format",
            "json",
        ],
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["kind"] == "verifier"
    assert payload["target_id"] == "run-1"
    assert payload["metadata"]["log_dir"] == ".custom-logs"


def test_register_cli_can_start_watcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait register CLI can start detached watcher."""

    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        "agent_maintainer.wait.cli_background.start_wait_watcher",
        lambda root, wait_id: calls.append((root, wait_id)),
    )

    status = cli.main(
        ["register", "github-pr", PR_NUMBER, "--root", str(tmp_path), "--start-watcher"],
    )

    assert status == 0
    assert len(calls) == 1
    assert calls[0][0] == tmp_path
    assert calls[0][1] in capsys.readouterr().out


def test_sweep_once_cli_prints_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait sweep once CLI renders compact summary."""

    monkeypatch.setattr(
        cli,
        "sweep_once",
        lambda _registry: cli.SweepSummary(checked=1, updated=1, pending=0, ready=1),
    )

    status = cli.main(["sweep", "--once", "--root", str(tmp_path)])

    output = capsys.readouterr().out
    assert status == 0
    assert "Result: PASS" in output
    assert "updated: 1" in output


def test_heartbeat_cli_stays_silent_without_ready_records(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Repo heartbeat prints nothing when no wait is ready."""

    status = cli.main(["heartbeat", "--root", str(tmp_path)])

    assert status == 0
    assert capsys.readouterr().out == ""


def test_heartbeat_cli_prints_ready_records_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Repo heartbeat renders ready capsules once."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_run(
        RegisterGitHubRunWait(root=tmp_path, run_id="123"),
    )
    registry.complete_github_run(
        record,
        GitHubWaitResult(
            run_id="123",
            state=GitHubRunState(
                status="completed",
                conclusion="success",
                url="https://run",
            ),
        ),
    )

    first_status = cli.main(["heartbeat", "--root", str(tmp_path)])
    first_output = capsys.readouterr().out
    second_status = cli.main(["heartbeat", "--root", str(tmp_path)])
    second_output = capsys.readouterr().out

    assert first_status == 0
    assert "Result: PASS" in first_output
    assert "GitHub run 123 reached PASS" in first_output
    assert second_status == 0
    assert second_output == ""


def test_sweep_once_completes_github_run(tmp_path: Path) -> None:
    """Sweeper dispatches GitHub run waits through the handler registry."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_run(
        RegisterGitHubRunWait(root=tmp_path, run_id="123"),
    )

    summary = sweep_once(
        registry,
        query_run=lambda _config: GitHubRunState(
            status="completed",
            conclusion="success",
            url="https://run",
        ),
    )

    completed = registry.read(record.wait_id)
    assert summary.updated == 1
    assert completed.ready
    assert completed.terminal_result == "PASS"


def test_sweep_once_completes_verifier(tmp_path: Path) -> None:
    """Sweeper dispatches verifier waits through the handler registry."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_verifier(
        RegisterVerifierWait(root=tmp_path, run_id="run-1"),
    )

    summary = sweep_once(
        registry,
        query_verifier=lambda _config: VerifierWaitResult(
            run_id="run-1",
            manifest=VerifierManifest(run_id="run-1", profile="fast", checks=()),
        ),
    )

    completed = registry.read(record.wait_id)
    assert summary.updated == 1
    assert completed.ready
    assert completed.terminal_result == "PASS"


def test_sweep_watch_cli_prints_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait sweep watch CLI renders final resume text."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number=PR_NUMBER),
    )
    completed = registry.complete_github_pr(
        record,
        GitHubPrWaitResult(
            pr_number=PR_NUMBER,
            state=GitHubPrChecksState(
                pr_number=PR_NUMBER,
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        ),
    )
    monkeypatch.setattr(cli, "watch_wait", lambda _registry, _wait_id: completed)

    status = cli.main(["sweep", "--watch", record.wait_id, "--root", str(tmp_path)])

    output = capsys.readouterr().out
    assert status == 0
    assert "Result: PASS" in output
    assert "Continuation:" in output


def assert_success(status: int) -> None:
    """Assert success without repeating assertion expressions."""

    assert status == 0
