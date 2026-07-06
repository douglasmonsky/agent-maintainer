"""Tests PR wait hook handoff behavior."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

from agent_maintainer.hooks import pr_wait
from agent_maintainer.wait.github_pr import GitHubPrCheck, GitHubPrChecksState, GitHubPrWaitResult


def pr_create_payload() -> dict[str, object]:
    """Return a Codex/Claude-style hook payload for a created PR."""
    return {
        "tool_name": "Bash",
        "tool_input": {"command": "gh pr create --base main --head codex/example"},
        "tool_response": {"stdout": "https://github.com/douglasmonsky/agent-maintainer/pull/293\n"},
    }


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


def test_codex_handoff_emits_post_tool_use_continuation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Codex gets a continuation because Codex command-hook async is unsupported."""
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(pr_create_payload())))

    status = pr_wait.run_hook(platform=pr_wait.CODEX_PLATFORM, repo_root=tmp_path)

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["decision"] == "block"
    assert "wait github-pr 293" in payload["reason"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


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
