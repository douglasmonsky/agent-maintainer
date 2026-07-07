"""Hook handoff for pull-request check waiting after PR creation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_client_hooks.constants import CLAUDE_CODE_PLATFORM, CODEX_PLATFORM
from agent_maintainer.wait.github_pr import (
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
    render_github_pr_wait_text,
    wait_for_github_pr_checks,
)
from agent_maintainer.wait.registry import RegisterGitHubPrWait, WaitRegistry
from agent_maintainer.wait.sweeper import start_wait_watcher

ASYNC_REWAKE_EXIT_CODE = 2
BACKGROUND_PR_WAIT_ENV = "AGENT_MAINTAINER_BACKGROUND_PR_WAIT"
DEFAULT_INTERVAL_SECONDS = 20
DEFAULT_TIMEOUT_SECONDS = 1800
GH_PR_CREATE_PATTERN = re.compile(r"(?:^|[;&|]\s*|\s)gh\s+pr\s+create\b")
PR_URL_PATTERN = re.compile(r"github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")


@dataclass(frozen=True)
class PrWaitHandoff:
    """One detected PR wait handoff from hook input."""

    pr_number: str
    repo: str | None = None


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse PR wait hook arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer.hooks.pr_wait")
    parser.add_argument("--platform", required=True, choices=(CODEX_PLATFORM, CLAUDE_CODE_PLATFORM))
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--async-rewake", action="store_true")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run PR wait hook command."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return run_hook(
        platform=args.platform,
        repo_root=args.repo_root or Path.cwd(),
        async_rewake=args.async_rewake,
        interval_seconds=args.interval,
        timeout_seconds=args.timeout_seconds,
    )


def run_hook(
    *,
    platform: str,
    repo_root: Path,
    async_rewake: bool = False,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> int:
    """Handle a PR-create tool result by waiting or handing off a wait command."""
    repo_root = repo_root.resolve()
    handoff = detect_handoff(read_hook_payload())
    if handoff is None:
        return 0

    if platform == CLAUDE_CODE_PLATFORM and async_rewake:
        result = wait_for_github_pr_checks(
            GitHubPrWaitConfig(
                pr_number=handoff.pr_number,
                repo=handoff.repo,
                interval_seconds=interval_seconds,
                timeout_seconds=timeout_seconds,
            )
        )
        print(render_rewake_message(result), file=sys.stderr)
        return ASYNC_REWAKE_EXIT_CODE

    if platform == CODEX_PLATFORM and background_pr_wait_enabled():
        return emit_codex_background_handoff(
            handoff,
            repo_root,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        )

    if platform == CODEX_PLATFORM:
        return emit_codex_handoff(handoff)

    return emit_sync_handoff(handoff)


def read_hook_payload() -> dict[str, object]:
    """Read hook JSON stdin, treating malformed input as empty."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def detect_handoff(payload: dict[str, object]) -> PrWaitHandoff | None:
    """Return PR wait handoff when a hook payload created a GitHub PR."""
    command = command_text(payload.get("tool_input"))
    if not GH_PR_CREATE_PATTERN.search(command):
        return None

    response_text = "\n".join(iter_text(payload.get("tool_response")))
    return handoff_from_text(response_text)


def command_text(value: object) -> str:
    """Return shell command text from hook tool input."""
    if isinstance(value, dict):
        command = value.get("command")
        return command if isinstance(command, str) else ""
    return value if isinstance(value, str) else ""


def handoff_from_text(text: str) -> PrWaitHandoff | None:
    """Extract PR repository and number from GitHub CLI output text."""
    match = PR_URL_PATTERN.search(text)
    if match is None:
        return None
    return PrWaitHandoff(repo=match.group(1), pr_number=match.group(2))


def iter_text(value: object) -> tuple[str, ...]:
    """Return text leaves from nested hook response data."""
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for item in value.values() for text in iter_text(item))
    if isinstance(value, list):
        return tuple(text for item in value for text in iter_text(item))
    return ()


def background_pr_wait_enabled() -> bool:
    """Return whether Codex PR waits should register background waits."""

    return os.environ.get(BACKGROUND_PR_WAIT_ENV) == "1"


def emit_codex_handoff(handoff: PrWaitHandoff) -> int:
    """Ask Codex to wait for PR checks through PostToolUse continuation."""
    command = wait_command(handoff)
    reason = (
        f"Pull request #{handoff.pr_number} was opened. "
        f"Wait for checks before reviewing or merging:\n{command}"
    )
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": reason,
                },
            }
        )
    )
    return 0


def emit_codex_background_handoff(
    handoff: PrWaitHandoff,
    repo_root: Path,
    *,
    interval_seconds: int,
    timeout_seconds: int,
) -> int:
    """Register a background Codex PR wait and emit one compact handoff."""

    record = WaitRegistry(repo_root).register_github_pr(
        RegisterGitHubPrWait(
            root=repo_root,
            pr_number=handoff.pr_number,
            repo=handoff.repo,
            platform=CODEX_PLATFORM,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        ),
    )
    try:
        start_wait_watcher(repo_root, record.wait_id)
    except OSError:
        return emit_codex_handoff(handoff)
    reason = (
        f"Pull request #{handoff.pr_number} was opened. "
        "Background check wait registered. Resume when ready:\n"
        f"{record.resume_instruction}"
    )
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": reason,
                },
            }
        )
    )
    return 0


def emit_sync_handoff(handoff: PrWaitHandoff) -> int:
    """Emit a generic synchronous handoff for non-Codex clients."""
    print(wait_command(handoff), file=sys.stderr)
    return ASYNC_REWAKE_EXIT_CODE


def render_rewake_message(result: GitHubPrWaitResult) -> str:
    """Render Claude async-rewake message after PR checks reach a final state."""
    text = render_github_pr_wait_text(result)
    if result.exit_code == 0:
        return (
            f"{text}\n\n"
            f"PR checks passed for #{result.pr_number}. Review the PR and merge if satisfactory."
        )
    return f"{text}\n\nPR checks are not passing for #{result.pr_number}; inspect before merging."


def wait_command(handoff: PrWaitHandoff) -> str:
    """Return explicit PR wait command for an agent continuation."""
    command = f"python -m agent_maintainer wait github-pr {handoff.pr_number}"
    if handoff.repo:
        return f"{command} --repo {handoff.repo}"
    return command


if __name__ == "__main__":
    sys.exit(main())
