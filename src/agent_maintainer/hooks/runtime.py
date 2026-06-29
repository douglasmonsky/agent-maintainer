"""Shared runtime for agent-client hook wrappers."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
import sys
import time
from contextlib import suppress
from pathlib import Path

from agent_maintainer.hooks import audit as hook_audit
from agent_maintainer.hooks import context as hook_context

CODEX_PLATFORM = "codex"
CLAUDE_CODE_PLATFORM = "claude-code"
POST_TOOL_USE_EVENT = "PostToolUse"
STOP_EVENT = "Stop"
SUBAGENT_STOP_EVENT = "SubagentStop"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse hook runtime arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer.hooks.runtime")
    parser.add_argument("--platform", required=True, choices=(CODEX_PLATFORM, CLAUDE_CODE_PLATFORM))
    parser.add_argument("--event", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--repo-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the hook runtime from a module command."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    return run_hook(
        platform=args.platform,
        event=args.event,
        profile=args.profile,
        repo_root=args.repo_root or discover_repo_root(Path.cwd()),
    )


def run_hook(*, platform: str, event: str, profile: str, repo_root: Path) -> int:
    """Run Agent Maintainer verification for one hook event."""

    payload = read_hook_payload()
    if is_recursive_stop(event, payload):
        return emit_continue()

    repo_root = repo_root.resolve()
    if not maintainer_configured(repo_root):
        return emit_success(event)

    started_at = hook_audit.utc_timestamp()
    started = time.monotonic()
    if not verifier_available(repo_root):
        expected_package = repo_root / "src" / "agent_maintainer"
        hook_audit.record_hook_result(
            repo_root,
            hook_audit.HookAuditRecord(
                platform=platform,
                hook_name=event,
                profile=profile,
                status="failed",
                command=(),
                exit_code=None,
                started_at=started_at,
                ended_at=hook_audit.utc_timestamp(),
                duration_seconds=hook_audit.duration_since(started),
                reason="missing verifier",
            ),
        )
        return emit_block(
            event=event,
            reason="Agent Maintainer verifier missing.",
            context=(
                "Expected verifier package at "
                f"{expected_package} or an installed "
                "`agent-maintainer` command. Run bootstrap/install before "
                "continuing."
            ),
        )

    command = verifier_command(repo_root, profile)
    result = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        env=hook_audit.hook_env_with_src(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    hook_audit.record_hook_result(
        repo_root,
        hook_audit.HookAuditRecord(
            platform=platform,
            hook_name=event,
            profile=profile,
            status=hook_audit.status_for_exit(result.returncode),
            command=tuple(command),
            exit_code=result.returncode,
            started_at=started_at,
            ended_at=hook_audit.utc_timestamp(),
            duration_seconds=hook_audit.duration_since(started),
        ),
    )
    if result.returncode == 0:
        return emit_success(event)

    config = hook_context.hook_config(repo_root)
    return emit_block(
        event=event,
        reason=block_reason(event),
        context=hook_context.failure_context(
            repo_root,
            result,
            config,
            config.context_hook_budget_chars,
        ),
    )


def read_hook_payload() -> dict[str, object]:
    """Read hook JSON from stdin, treating malformed input as empty."""

    with suppress(json.JSONDecodeError, OSError):
        payload = json.load(sys.stdin)
        if isinstance(payload, dict):
            return payload
    return {}


def is_recursive_stop(event: str, payload: dict[str, object]) -> bool:
    """Return whether a stop hook is already active for this event."""

    return event in {STOP_EVENT, SUBAGENT_STOP_EVENT} and payload.get("stop_hook_active") is True


def discover_repo_root(cwd: Path) -> Path:
    """Return the Git repository root for hook execution."""

    git_path = shutil.which("git")
    if git_path is None:
        return cwd
    result = subprocess.run(  # nosec B603
        [git_path, "rev-parse", "--show-toplevel"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return cwd


def maintainer_configured(repo_root: Path) -> bool:
    """Return whether this repository has opted into Agent Maintainer hooks."""

    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return False
    with suppress(OSError):
        return "[tool.agent_maintainer]" in pyproject.read_text(encoding="utf-8")
    return False


def verifier_command(repo_root: Path, profile: str) -> list[str]:
    """Return verifier command for a hook execution."""

    if not (repo_root / "src" / "agent_maintainer" / "__main__.py").exists():
        return ["agent-maintainer", "verify", "--profile", profile, "--base-ref", "HEAD"]
    return [
        verifier_python(repo_root),
        "-m",
        "agent_maintainer",
        "verify",
        "--profile",
        profile,
        "--base-ref",
        "HEAD",
    ]


def verifier_python(repo_root: Path) -> str:
    """Prefer a repository virtualenv interpreter for verification."""

    for relative in (".venv/bin/python", "venv/bin/python"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return sys.executable


def package_command_available() -> bool:
    """Return whether the console script is available for global hooks."""

    return shutil.which("agent-maintainer") is not None


def verifier_available(repo_root: Path) -> bool:
    """Return whether a repo-local or installed verifier is available."""

    repo_local = (repo_root / "src" / "agent_maintainer" / "__main__.py").exists()
    return repo_local or package_command_available()


def emit_success(event: str) -> int:
    """Emit a success response appropriate for the hook event."""

    if event in {STOP_EVENT, SUBAGENT_STOP_EVENT}:
        return emit({"continue": True})
    return 0


def emit_block(*, event: str, reason: str, context: str) -> int:
    """Emit a hook block decision for supported agent clients."""

    if event == POST_TOOL_USE_EVENT:
        return emit(
            {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": context,
                },
            }
        )
    return emit({"decision": "block", "reason": f"{reason}\n\n{context}"})


def emit_continue() -> int:
    """Emit a continuation response for recursive stop-hook calls."""

    return emit({"continue": True})


def emit(payload: dict[str, object]) -> int:
    """Emit one JSON hook response."""

    print(json.dumps(payload))
    return 0


def block_reason(event: str) -> str:
    """Return concise block reason by hook event."""

    if event == POST_TOOL_USE_EVENT:
        return "Fast Agent Maintainer checks failed after edit."
    return "Final verification failed. Fix issues before finishing."


if __name__ == "__main__":
    sys.exit(main())
