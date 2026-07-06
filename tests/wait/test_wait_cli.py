"""Tests quiet wait CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.runtime_events.sinks import InMemoryRuntimeEventSink
from agent_maintainer.runtime_events.waiting import WaitRuntimeEvents
from agent_maintainer.wait import cli
from agent_maintainer.wait.github import GitHubRunState, GitHubWaitConfig, GitHubWaitResult
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRegistry
from agent_maintainer.wait.verifier import VerifierManifest, VerifierWaitResult

SUCCESS_TIMEOUT_SECONDS = 2
ERROR_EXIT_CODE = 2


def test_poll_observer_helpers_emit_events() -> None:
    """Wait CLI observer helpers emit compact poll events."""

    sink = InMemoryRuntimeEventSink()
    runtime_events = WaitRuntimeEvents(
        sink=sink,
        target_kind="github-run",
        target_id="123",
    )

    cli._observe_github_run(
        runtime_events,
        1,
        GitHubRunState(status="completed", conclusion="success", url="https://run"),
    )
    cli._observe_github_pr(
        runtime_events,
        2,
        GitHubPrChecksState(
            pr_number="303",
            checks=(GitHubPrCheck(name="verify", state="success"),),
        ),
    )

    assert [record["event_name"] for record in sink.records] == [
        "wait.poll",
        "wait.poll",
    ]
    run_attributes = cast("dict[str, object]", sink.records[0]["attributes"])
    pr_attributes = cast("dict[str, object]", sink.records[1]["attributes"])
    assert run_attributes["conclusion"] == "success"
    assert pr_attributes["check_count"] == 1


def test_github_run_cli_prints_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """GitHub run CLI prints only final success status."""
    fake_wait = SuccessWait()
    monkeypatch.setattr(cli, "wait_for_github_run", fake_wait)

    status = cli.main(["github-run", "123", "--interval", "1", "--timeout-seconds", "2"])

    assert status == 0
    assert fake_wait.seen_config == GitHubWaitConfig(
        run_id="123",
        interval_seconds=1,
        timeout_seconds=SUCCESS_TIMEOUT_SECONDS,
    )
    assert capsys.readouterr().out == (
        "Result: PASS\nRun ID: 123\n\nExpand only if needed:\nhttps://run\n"
    )


def test_github_run_cli_json_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """GitHub run CLI preserves nonzero status for failed runs."""
    monkeypatch.setattr(cli, "wait_for_github_run", failure_wait)

    status = cli.main(["github-run", "123", "--format", "json"])

    output = capsys.readouterr().out
    assert status == 1
    assert '"conclusion": "failure"' in output
    assert '"exit_code": 1' in output


def test_github_run_cli_reports_query_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """GitHub CLI query errors become compact repair output."""
    monkeypatch.setattr(cli, "wait_for_github_run", error_wait)

    status = cli.main(["github-run", "123"])

    output = capsys.readouterr().out
    assert status == ERROR_EXIT_CODE
    assert "Result: ERROR" in output
    assert "gh auth required" in output


def test_github_pr_cli_prints_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """GitHub PR CLI prints only final success status."""
    fake_wait = SuccessPrWait()
    monkeypatch.setattr(cli, "wait_for_github_pr_checks", fake_wait)

    status = cli.main(["github-pr", "291", "--interval", "1", "--timeout-seconds", "2"])

    assert status == 0
    assert fake_wait.seen_config == GitHubPrWaitConfig(
        pr_number="291",
        interval_seconds=1,
        timeout_seconds=SUCCESS_TIMEOUT_SECONDS,
    )
    assert capsys.readouterr().out == "Result: PASS\nRun ID: PR #291\n"


def test_verifier_cli_prints_manifest_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verifier wait CLI prints compact manifest-backed status."""
    monkeypatch.setattr(cli, "wait_for_verifier_run", verifier_wait)

    status = cli.main(["verifier", "run-1", "--format", "text"])

    assert status == 0
    assert capsys.readouterr().out == ("Result: PASS\nProfile: fast\nRun ID: run-1\n")


def test_verifier_cli_json_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verifier wait CLI supports machine-readable output."""
    monkeypatch.setattr(cli, "wait_for_verifier_run", verifier_wait)

    status = cli.main(["verifier", "run-1", "--format", "json"])

    output = capsys.readouterr().out
    assert status == 0
    assert '"profile": "fast"' in output
    assert '"status": "passed"' in output


def test_register_github_pr_cli_writes_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait register CLI persists PR waits and renders JSON."""

    status = cli.main(
        [
            "register",
            "github-pr",
            "291",
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
        "pr_number": "291",
        "repo": "douglasmonsky/agent-maintainer",
        "platform": "codex",
    }

    assert status == 0
    assert {field: payload[field] for field in expected_fields} == expected_fields
    assert "wait resume" in payload["resume_instruction"]
    assert (tmp_path / ".verify-logs" / "waits" / f"{payload['wait_id']}.json").exists()


def test_resume_github_pr_cli_prints_continuation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait resume CLI renders terminal continuation text."""

    registry = WaitRegistry(tmp_path)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=tmp_path, pr_number="291"),
    )
    completed = registry.complete_github_pr(
        record,
        GitHubPrWaitResult(
            pr_number="291",
            state=GitHubPrChecksState(
                pr_number="291",
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        ),
    )

    status = cli.main(["resume", completed.wait_id, "--root", str(tmp_path)])

    output = capsys.readouterr().out
    assert status == 0
    assert output.startswith("Result: PASS\nRun ID: PR #291")
    assert "Continuation:" in output
    assert "PR checks reached PASS for PR #291" in output


def test_resume_cli_parser_accepts_root(tmp_path: Path) -> None:
    """Wait resume parser accepts explicit root and JSON output."""

    args = cli.parse_args(
        ["resume", "wait-1", "--root", str(tmp_path), "--format", "json"],
    )

    assert args.command == "resume"
    assert args.wait_id == "wait-1"
    assert args.root == tmp_path
    assert args.format == "json"


class SuccessWait:
    """Fake successful GitHub waiter capturing config."""

    def __init__(self) -> None:
        self.seen_config: GitHubWaitConfig | None = None

    def __call__(self, config: GitHubWaitConfig, **_kwargs: object) -> GitHubWaitResult:
        self.seen_config = config
        return GitHubWaitResult(
            run_id=config.run_id,
            state=GitHubRunState(status="completed", conclusion="success", url="https://run"),
        )


class SuccessPrWait:
    """Fake successful GitHub PR waiter capturing config."""

    def __init__(self) -> None:
        self.seen_config: GitHubPrWaitConfig | None = None

    def __call__(
        self,
        config: GitHubPrWaitConfig,
        **_kwargs: object,
    ) -> GitHubPrWaitResult:
        self.seen_config = config
        return GitHubPrWaitResult(
            pr_number=config.pr_number,
            state=GitHubPrChecksState(
                pr_number=config.pr_number,
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        )


def failure_wait(config: GitHubWaitConfig, **_kwargs: object) -> GitHubWaitResult:
    """Return one failed GitHub wait result."""
    return GitHubWaitResult(
        run_id=config.run_id,
        state=GitHubRunState(status="completed", conclusion="failure", url="https://run"),
    )


def error_wait(_config: GitHubWaitConfig, **_kwargs: object) -> GitHubWaitResult:
    """Raise a GitHub query error."""
    raise RuntimeError("gh auth required")


def verifier_wait(_config: object, **_kwargs: object) -> VerifierWaitResult:
    """Return verifier pass result."""
    return VerifierWaitResult(
        run_id="run-1",
        manifest=VerifierManifest(run_id="run-1", profile="fast"),
    )
