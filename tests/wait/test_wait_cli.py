"""Tests quiet wait CLI commands."""

from __future__ import annotations

import pytest

from agent_maintainer.wait import cli
from agent_maintainer.wait.github import GitHubRunState, GitHubWaitConfig, GitHubWaitResult
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.verifier import VerifierManifest, VerifierWaitResult

SUCCESS_TIMEOUT_SECONDS = 2
ERROR_EXIT_CODE = 2


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


class SuccessWait:
    """Fake successful GitHub waiter capturing config."""

    def __init__(self) -> None:
        self.seen_config: GitHubWaitConfig | None = None

    def __call__(self, config: GitHubWaitConfig) -> GitHubWaitResult:
        self.seen_config = config
        return GitHubWaitResult(
            run_id=config.run_id,
            state=GitHubRunState(status="completed", conclusion="success", url="https://run"),
        )


class SuccessPrWait:
    """Fake successful GitHub PR waiter capturing config."""

    def __init__(self) -> None:
        self.seen_config: GitHubPrWaitConfig | None = None

    def __call__(self, config: GitHubPrWaitConfig) -> GitHubPrWaitResult:
        self.seen_config = config
        return GitHubPrWaitResult(
            pr_number=config.pr_number,
            state=GitHubPrChecksState(
                pr_number=config.pr_number,
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        )


def failure_wait(config: GitHubWaitConfig) -> GitHubWaitResult:
    """Return one failed GitHub wait result."""
    return GitHubWaitResult(
        run_id=config.run_id,
        state=GitHubRunState(status="completed", conclusion="failure", url="https://run"),
    )


def error_wait(_config: GitHubWaitConfig) -> GitHubWaitResult:
    """Raise a GitHub query error."""
    raise RuntimeError("gh auth required")


def verifier_wait(_config: object) -> VerifierWaitResult:
    """Return verifier pass result."""
    return VerifierWaitResult(
        run_id="run-1",
        manifest=VerifierManifest(run_id="run-1", profile="fast"),
    )
