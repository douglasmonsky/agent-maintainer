"""Tests PR wait hook handoff behavior."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

from agent_maintainer.hooks import pr_wait
from agent_maintainer.wait import daemon_launchd
from agent_maintainer.wait.github_pr import GitHubPrCheck, GitHubPrChecksState, GitHubPrWaitResult


def pr_create_payload() -> dict[str, object]:
    """Return a Codex/Claude-style hook payload for a created PR."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "gh pr create --base main --head codex/example"},
        "tool_response": {"stdout": "https://github.com/douglasmonsky/agent-maintainer/pull/293\n"},
    }


def fail_start_watcher(_root: Path, _wait_id: str) -> None:
    """Raise the watcher spawn error used by fallback coverage."""
    raise OSError("spawn failed")


def test_detect_handoff_extracts_pr_url() -> None:
    """PR-create hook payloads extract repository and PR number."""
    handoff = pr_wait.detect_handoff(pr_create_payload())

    assert handoff == pr_wait.PrWaitHandoff(
        repo="douglasmonsky/agent-maintainer",
        pr_number="293",
    )


def test_detect_handoff_ignores_other_bash_commands() -> None:
    """Non-PR-create commands do not trigger wait handoff."""
    payload = pr_create_payload()
    payload["tool_input"] = {"command": "gh pr view 293"}

    assert pr_wait.detect_handoff(payload) is None


def test_main_delegates_parsed_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR wait hook CLI parses arguments and delegates runtime."""
    calls: list[dict[str, object]] = []

    def fake_run_hook(**kwargs: object) -> int:
        calls.append(kwargs)
        return pr_wait.ASYNC_REWAKE_EXIT_CODE

    monkeypatch.setattr(pr_wait, "run_hook", fake_run_hook)

    status = pr_wait.main(
        [
            "--platform",
            pr_wait.CLAUDE_CODE_PLATFORM,
            "--repo-root",
            str(tmp_path),
            "--async-rewake",
            "--interval",
            "1",
            "--timeout-seconds",
            "2",
        ]
    )

    assert status == pr_wait.ASYNC_REWAKE_EXIT_CODE
    assert calls == [
        {
            "platform": pr_wait.CLAUDE_CODE_PLATFORM,
            "repo_root": tmp_path,
            "async_rewake": True,
            "interval_seconds": 1,
            "timeout_seconds": 2,
        }
    ]


def test_run_hook_ignores_non_pr_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hooks no-op when payload did not create a PR."""
    monkeypatch.setattr(sys, "stdin", StringIO('{"tool_input": {"command": "date"}}'))

    assert pr_wait.run_hook(platform=pr_wait.CODEX_PLATFORM, repo_root=tmp_path) == 0


def test_payload_helpers_handle_malformed_and_unmatched_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Payload helpers tolerate malformed hook input and missing PR URLs."""
    monkeypatch.setattr(sys, "stdin", StringIO("{"))

    assert pr_wait.read_hook_payload() == {}
    assert pr_wait.command_text("gh pr create --fill") == "gh pr create --fill"
    assert pr_wait.command_text({"command": 293}) == ""
    assert pr_wait.handoff_from_text("Created pull request") is None
    assert pr_wait.iter_text(["a", {"b": ["c", None]}]) == ("a", "c")


def test_codex_handoff_emits_post_tool_use_continuation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex gets a continuation when background waits are disabled."""
    monkeypatch.setenv(pr_wait.BACKGROUND_PR_WAIT_ENV, "0")
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(pr_create_payload())))

    status = pr_wait.run_hook(platform=pr_wait.CODEX_PLATFORM, repo_root=tmp_path)

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["decision"] == "block"
    assert "wait github-pr 293" in payload["reason"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


def test_codex_background_wait_registers_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex background PR wait registers durable wait state."""
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(pr_create_payload())))
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.ensure_wait_daemon",
        lambda root, wait_id: (
            calls.append((root, wait_id))
            or daemon_launchd.DaemonLaunch(
                started=True,
                label="com.agent-maintainer.wait.test",
                log_path=tmp_path / "daemon.log",
            )
        ),
    )

    status = pr_wait.run_hook(
        platform=pr_wait.CODEX_PLATFORM,
        repo_root=tmp_path,
        interval_seconds=1,
        timeout_seconds=2,
    )

    payload = json.loads(capsys.readouterr().out)
    wait_files = tuple((tmp_path / ".verify-logs" / "waits").glob("*.json"))
    assert status == 0
    assert len(calls) == 1
    assert len(wait_files) == 1
    assert "watcher: started via launchd" in payload["reason"]
    assert "wait resume" in payload["reason"]
    assert "fallback heartbeat request:" in payload["reason"]
    assert '"wait_kind": "github-pr"' in payload["reason"]
    assert "python -m agent_maintainer wait github-pr" not in payload["reason"]


def test_codex_bg_wait_survives_spawn_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex background wait still returns manual resume when watcher fails."""
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(pr_create_payload())))
    monkeypatch.setattr(
        "agent_maintainer.wait.broker.start_wait_watcher",
        fail_start_watcher,
    )

    status = pr_wait.run_hook(platform=pr_wait.CODEX_PLATFORM, repo_root=tmp_path)

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert "wait resume" in payload["reason"]
    assert "fallback heartbeat request:" in payload["reason"]
    assert "wait github-pr 293" not in payload["reason"]
    assert payload["decision"] == "block"


def test_claude_async_rewake_waits_and_exits_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Claude async-rewake hook waits and wakes with final PR status."""
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(pr_create_payload())))

    seen_configs: list[pr_wait.GitHubPrWaitConfig] = []

    def fake_wait(config: pr_wait.GitHubPrWaitConfig) -> GitHubPrWaitResult:
        seen_configs.append(config)
        return GitHubPrWaitResult(
            pr_number=config.pr_number,
            state=GitHubPrChecksState(
                pr_number=config.pr_number,
                checks=(GitHubPrCheck(name="verify", state="success", bucket="pass"),),
            ),
        )

    monkeypatch.setattr(pr_wait, "wait_for_github_pr_checks", fake_wait)

    status = pr_wait.run_hook(
        platform=pr_wait.CLAUDE_CODE_PLATFORM,
        repo_root=tmp_path,
        async_rewake=True,
        interval_seconds=1,
        timeout_seconds=2,
    )

    captured = capsys.readouterr()
    assert status == pr_wait.ASYNC_REWAKE_EXIT_CODE
    assert captured.out == ""
    assert "Result: PASS" in captured.err
    assert "Review the PR and merge if satisfactory" in captured.err
    assert seen_configs == [
        pr_wait.GitHubPrWaitConfig(
            pr_number="293",
            repo="douglasmonsky/agent-maintainer",
            interval_seconds=1,
            timeout_seconds=2,
        )
    ]


def test_claude_sync_handoff_exits_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Non-async Claude hook receives compact wait command handoff."""
    payload = pr_create_payload()
    payload["tool_response"] = {"stdout": "https://github.com/example/repo/pull/7\n"}
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(payload)))

    status = pr_wait.run_hook(
        platform=pr_wait.CLAUDE_CODE_PLATFORM,
        repo_root=tmp_path,
        async_rewake=False,
    )

    captured = capsys.readouterr()
    assert status == pr_wait.ASYNC_REWAKE_EXIT_CODE
    assert captured.out == ""
    assert "wait github-pr 7 --repo example/repo" in captured.err


def test_rewake_failure_message_and_wait_command_without_repo() -> None:
    """Failure rendering and repo-less wait commands stay compact."""
    result = GitHubPrWaitResult(
        pr_number="7",
        state=GitHubPrChecksState(
            pr_number="7",
            checks=(GitHubPrCheck(name="verify", state="failure", bucket="fail"),),
        ),
    )

    assert "not passing" in pr_wait.render_rewake_message(result)
    assert pr_wait.wait_command(pr_wait.PrWaitHandoff(pr_number="7")) == (
        "python -m agent_maintainer wait github-pr 7"
    )
