"""Shared runtime for agent-client hook wrappers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_client_hooks import constants as hook_constants
from agent_maintainer.hooks import (
    audit as hook_audit,
)
from agent_maintainer.hooks import (
    context as hook_context,
)
from agent_maintainer.hooks import (
    discovery as hook_discovery,
)
from agent_maintainer.hooks import (
    readiness as hook_readiness,
)
from agent_maintainer.hooks import (
    runtime_eventing,
    runtime_payload,
)
from agent_maintainer.hooks import (
    subprocess_runner as hook_subprocess,
)

CODEX_PLATFORM = hook_constants.CODEX_PLATFORM
CLAUDE_CODE_PLATFORM = hook_constants.CLAUDE_CODE_PLATFORM
POST_TOOL_USE_EVENT = hook_constants.POST_TOOL_USE_EVENT
STOP_EVENT = hook_constants.STOP_EVENT
SUBAGENT_STOP_EVENT = hook_constants.SUBAGENT_STOP_EVENT


def parse_args(argv: list[str]):
    """Parse hook runtime arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer.hooks.runtime")
    parser.add_argument("--platform", required=True, choices=(CODEX_PLATFORM, CLAUDE_CODE_PLATFORM))
    parser.add_argument("--event", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--async-rewake", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the hook runtime from a module command."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    return run_hook(
        platform=args.platform,
        event=args.event,
        profile=args.profile,
        repo_root=args.repo_root or hook_discovery.discover_repo_root(Path.cwd()),
        async_rewake=args.async_rewake,
    )


# docsync:evidence.start evidence.agent_hooks.configured_repo_noop
def run_hook(
    *,
    platform: str,
    event: str,
    profile: str,
    repo_root: Path,
    async_rewake: bool = False,
) -> int:
    """Run Agent Maintainer verification for one hook event."""

    payload = read_hook_payload()
    repo_root = repo_root.resolve()
    if not maintainer_configured(repo_root):
        return emit_success(event)

    started_at = hook_audit.utc_timestamp()
    started = hook_audit.monotonic_timestamp()
    runtime_events = runtime_eventing.HookRuntimeEvents.create(
        repo_root,
        platform=platform,
        event=event,
        profile=profile,
    )
    runtime_events.invoked(repo_configured=True)
    if is_recursive_stop(event, payload):
        runtime_events.finished(
            status="recursive_noop",
            exit_code=0,
            duration_seconds=hook_audit.duration_since(started),
        )
        return emit_continue()
    if not verifier_available(repo_root):
        duration_seconds = hook_audit.duration_since(started)
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
                duration_seconds=duration_seconds,
                reason="missing verifier",
            ),
        )
        runtime_events.finished(
            status="missing_verifier",
            exit_code=None,
            duration_seconds=duration_seconds,
        )
        return emit_block(
            event=event,
            reason="Agent Maintainer verifier missing.",
            context=missing_verifier_context(repo_root),
            async_rewake=async_rewake,
        )

    readiness = hook_readiness.hook_readiness(repo_root, profile)
    if readiness is not None:
        return emit_readiness(
            hook_readiness.HookExecution(
                repo_root=repo_root,
                platform=platform,
                event=event,
                profile=profile,
                started_at=started_at,
                started=started,
                runtime_events=runtime_events,
            ),
            readiness,
            async_rewake=async_rewake,
        )

    command = verifier_command(repo_root, profile)
    try:
        result = hook_subprocess.run_verifier_bounded(command, repo_root)
    except Exception as exc:
        runtime_events.exception(exc, duration_seconds=hook_audit.duration_since(started))
        raise
    duration_seconds = hook_audit.duration_since(started)
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
            duration_seconds=duration_seconds,
        ),
    )
    runtime_events.finished(
        status=hook_audit.status_for_exit(result.returncode),
        exit_code=result.returncode,
        duration_seconds=duration_seconds,
    )
    return emit_verifier_result(
        event=event,
        repo_root=repo_root,
        result=result,
        async_rewake=async_rewake,
    )


def emit_verifier_result(
    *,
    event: str,
    repo_root: Path,
    result: hook_subprocess.subprocess.CompletedProcess[str],
    async_rewake: bool = False,
) -> int:
    """Emit success or block response for a completed verifier run."""
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
        async_rewake=async_rewake,
    )


def read_hook_payload() -> dict[str, object]:
    """Read hook JSON from stdin, treating malformed input as empty."""

    return runtime_payload.read_hook_payload(sys.stdin)


def is_recursive_stop(event: str, payload: dict[str, object]) -> bool:
    """Return whether a stop hook is already active for this event."""

    return event in {STOP_EVENT, SUBAGENT_STOP_EVENT} and payload.get("stop_hook_active") is True


def maintainer_configured(repo_root: Path) -> bool:
    """Return whether this repository has opted into Agent Maintainer hooks."""

    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        return "[tool.agent_maintainer]" in pyproject.read_text(encoding="utf-8")
    except OSError:
        return False


# docsync:evidence.end evidence.agent_hooks.configured_repo_noop


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

    return hook_discovery.command_available("agent-maintainer")


def missing_verifier_context(repo_root: Path) -> str:
    """Return setup repair context when hook verifier is unavailable."""
    expected_package = repo_root / "src" / "agent_maintainer"
    return (
        "Expected verifier package at "
        f"{expected_package} or an installed "
        "`agent-maintainer` command. Run bootstrap/install before continuing."
    )


def verifier_available(repo_root: Path) -> bool:
    """Return whether a repo-local or installed verifier is available."""

    repo_local = (repo_root / "src" / "agent_maintainer" / "__main__.py").exists()
    return repo_local or package_command_available()


def emit_success(event: str) -> int:
    """Emit a success response appropriate for the hook event."""

    if event in {STOP_EVENT, SUBAGENT_STOP_EVENT}:
        return emit({"continue": True})
    return 0


def emit_readiness(
    execution: hook_readiness.HookExecution,
    readiness: hook_readiness.HookReadiness,
    *,
    async_rewake: bool = False,
) -> int:
    """Emit hook response for same-state verifier readiness."""
    duration_seconds = hook_audit.duration_since(execution.started)
    status = readiness_status(readiness)
    hook_audit.record_hook_result(
        execution.repo_root,
        hook_audit.HookAuditRecord(
            platform=execution.platform,
            hook_name=execution.event,
            profile=execution.profile,
            status=status,
            command=(),
            exit_code=readiness.exit_code,
            started_at=execution.started_at,
            ended_at=hook_audit.utc_timestamp(),
            duration_seconds=duration_seconds,
            reason="same-state verifier readiness",
        ),
    )
    execution.runtime_events.finished(
        status=status,
        exit_code=readiness.exit_code,
        duration_seconds=duration_seconds,
    )
    if execution.platform == CODEX_PLATFORM and readiness.pending:
        return emit_block(
            event=execution.event,
            reason="Agent Maintainer verification already running.",
            context=hook_readiness.render_codex_background_wait(execution, readiness),
            async_rewake=False,
        )
    if readiness.passed:
        return emit_success(execution.event)
    reason = (
        "Agent Maintainer verification already running."
        if readiness.pending
        else block_reason(execution.event)
    )
    return emit_block(
        event=execution.event,
        reason=reason,
        context=hook_readiness.render_hook_readiness(readiness),
        async_rewake=async_rewake,
    )


def readiness_status(readiness: hook_readiness.HookReadiness) -> str:
    """Return hook audit status for verifier readiness."""
    if readiness.pending:
        return "pending"
    if readiness.passed:
        return "reused"
    return "failed"


def emit_block(
    *,
    event: str,
    reason: str,
    context: str,
    async_rewake: bool = False,
) -> int:
    """Emit a hook block decision for supported agent clients."""
    if async_rewake:
        print(f"{reason}\n\n{context}", file=sys.stderr)
        return 2

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

    print(runtime_payload.render_hook_payload(payload))
    return 0


def block_reason(event: str) -> str:
    """Return concise block reason by hook event."""

    if event == POST_TOOL_USE_EVENT:
        return "Fast Agent Maintainer checks failed after edit."
    return "Final verification failed. Fix issues before finishing."


if __name__ == "__main__":
    sys.exit(main())
