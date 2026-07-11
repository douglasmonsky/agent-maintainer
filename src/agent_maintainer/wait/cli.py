"""Quiet wait command entrypoint."""

from __future__ import annotations

import argparse
import json

from agent_maintainer.runtime_events.waiting import (
    WaitRuntimeEvents,
    emit_cleaned,
    emit_heartbeat_noop,
    emit_terminal_claimed,
)
from agent_maintainer.wait import (
    cli_background,
    cli_parsers,
    cli_register,
    codex_smoke,
    daemon,
    daemon_launchd,
)
from agent_maintainer.wait.codex_rewake import (
    CodexRewakeBackend,
    codex_rewake_resumed,
    render_codex_rewake_text,
)
from agent_maintainer.wait.github import (
    GitHubRunState,
    GitHubWaitConfig,
    GitHubWaitResult,
    render_github_wait_json,
    render_github_wait_text,
    wait_for_github_run,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrChecksState,
    GitHubPrWaitConfig,
    GitHubPrWaitResult,
    render_github_pr_wait_json,
    render_github_pr_wait_text,
    wait_for_github_pr_checks,
)
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry, wait_record_json
from agent_maintainer.wait.sweeper import (
    CleanupSummary,
    SweepSummary,
    cleanup_waits,
    sweep_once,
    sweep_ready_notifications,
    sweep_record,
    watch_wait,
)
from agent_maintainer.wait.sweeper_rendering import render_sweep_json, render_sweep_text
from agent_maintainer.wait.verifier import (
    VerifierWaitConfig,
    VerifierWaitResult,
    render_verifier_wait_json,
    render_verifier_wait_text,
    wait_for_verifier_run,
)

parse_args = cli_parsers.parse_args


def main(argv: list[str] | None = None) -> int:
    """Run quiet wait subcommands."""

    args = parse_args([] if argv is None else argv)
    handlers = {
        "github-run": _github_run,
        "github-pr": _github_pr,
        "verifier": _verifier_run,
        "register": cli_register.register_wait,
        "resume": _resume,
        "sweep": _sweep,
        "heartbeat": _heartbeat,
        "cleanup": _cleanup,
        "codex-smoke": _codex_smoke,
        "daemon": _daemon,
    }
    handler = handlers.get(args.command)
    if handler is not None:
        return handler(args)
    return 2


def _github_run(args: argparse.Namespace) -> int:
    background = cli_background.background_github_run_if_needed(args)
    if background is not None:
        print(cli_background.render_background(args.format, background))
        return 0
    result = _wait_github_run(args)
    if args.format == cli_parsers.JSON_FORMAT:
        print(render_github_wait_json(result))
    else:
        print(render_github_wait_text(result))
    return result.exit_code


def _github_pr(args: argparse.Namespace) -> int:
    background = cli_background.background_github_pr_if_needed(args)
    if background is not None:
        print(cli_background.render_background(args.format, background))
        return 0
    result = _wait_github_pr(args)
    if args.format == cli_parsers.JSON_FORMAT:
        print(render_github_pr_wait_json(result))
    else:
        print(render_github_pr_wait_text(result))
    return result.exit_code


def _verifier_run(args: argparse.Namespace) -> int:
    background = cli_background.background_verifier_if_needed(args)
    if background is not None:
        print(cli_background.render_background(args.format, background))
        return 0
    result = _wait_verifier(args)
    if args.format == cli_parsers.JSON_FORMAT:
        print(render_verifier_wait_json(result))
    else:
        print(render_verifier_wait_text(result))
    return result.exit_code


def _resume(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    record = registry.read(args.wait_id)
    if args.format == cli_parsers.JSON_FORMAT:
        print(wait_record_json(record))
    else:
        print(cli_background.render_resume(record))
    return 0


def _sweep(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    if args.once:
        summary = sweep_once(registry)
        cli_background.emit_swept(summary)
        print(_render_sweep(args.format, summary))
        return 0
    if args.one:
        record = sweep_record(registry, registry.read(args.one))
        return _render_sweep_record(
            registry,
            args.format,
            record,
            pending_is_silent=True,
        )
    record = watch_wait(registry, args.watch)
    return _render_sweep_record(
        registry,
        args.format,
        record,
        pending_is_silent=False,
    )


def _render_sweep_record(
    registry: WaitRegistry,
    output_format: str,
    record: WaitRecord,
    *,
    pending_is_silent: bool,
) -> int:
    if output_format == cli_parsers.JSON_FORMAT:
        print(wait_record_json(record))
        return 0
    if pending_is_silent and not record.ready:
        return 0
    cli_background.emit_ready(record)
    rewake = CodexRewakeBackend(registry).resume_if_available(record)
    if codex_rewake_resumed(rewake):
        cli_background.emit_resumed(record)
        print(render_codex_rewake_text(record, rewake))
        return 0
    print(cli_background.render_resume(record))
    return 0


def _heartbeat(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    ready_records = sweep_ready_notifications(registry)
    events = WaitRuntimeEvents.create(target_kind="repo", target_id="heartbeat")
    if ready_records:
        for ready_record in ready_records:
            emit_terminal_claimed(
                events,
                wait_id=ready_record.wait_id,
                result=ready_record.terminal_result,
            )
        print("\n\n".join(cli_background.render_resume(item) for item in ready_records))
    else:
        emit_heartbeat_noop(events)
    return 0


def _cleanup(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    summary = cleanup_waits(
        registry,
        ready_older_than_seconds=args.ready_older_than_seconds,
    )
    events = WaitRuntimeEvents.create(target_kind="repo", target_id="cleanup")
    emit_cleaned(events, expired_ready=summary.expired_ready)
    print(_render_cleanup(args.format, summary))
    return 0


def _codex_smoke(args: argparse.Namespace) -> int:
    result = codex_smoke.run_codex_smoke(
        start_turn=args.start_turn,
        timeout_seconds=args.timeout_seconds,
    )
    if args.format == cli_parsers.JSON_FORMAT:
        print(codex_smoke.render_codex_smoke_json(result))
    else:
        print(codex_smoke.render_codex_smoke_text(result))
    return result.exit_code


def _daemon(args: argparse.Namespace) -> int:
    if args.daemon_command == "run":
        return daemon.run_daemon(
            args.root,
            interval_seconds=args.interval,
            idle_timeout_seconds=args.idle_timeout,
        )
    if args.daemon_command == "install":
        result = daemon_launchd.install_launch_agent(
            args.root,
            options=daemon_launchd.LaunchAgentInstallOptions(
                interval_seconds=args.interval,
                idle_timeout_seconds=args.idle_timeout,
            ),
        )
        print(_render_daemon_launch(args.format, result))
        return 0 if result.started else 1
    if args.daemon_command == "uninstall":
        status = daemon_launchd.uninstall_launch_agent(args.root)
        print(_render_daemon_status(args.format, status))
        return 0
    if args.daemon_command == "status":
        status = daemon_launchd.daemon_status(args.root)
        print(_render_daemon_status(args.format, status))
        return 0 if status.loaded else 1
    return 2


def _wait_github_run(args: argparse.Namespace) -> GitHubWaitResult:
    config = GitHubWaitConfig(
        run_id=args.run_id,
        repo=args.repo,
        interval_seconds=args.interval,
        timeout_seconds=args.timeout_seconds,
    )
    runtime_events = WaitRuntimeEvents.create(
        target_kind="github-run",
        target_id=args.run_id,
    )
    try:
        return wait_for_github_run(
            config,
            poll_observer=lambda attempt, state: _observe_github_run(
                runtime_events,
                attempt,
                state,
            ),
        )
    except RuntimeError as exc:
        return GitHubWaitResult(run_id=args.run_id, state=None, error=str(exc))


def _wait_github_pr(args: argparse.Namespace) -> GitHubPrWaitResult:
    config = GitHubPrWaitConfig(
        pr_number=args.pr_number,
        repo=args.repo,
        interval_seconds=args.interval,
        timeout_seconds=args.timeout_seconds,
    )
    runtime_events = WaitRuntimeEvents.create(
        target_kind="github-pr",
        target_id=args.pr_number,
    )
    try:
        return wait_for_github_pr_checks(
            config,
            poll_observer=lambda attempt, state: _observe_github_pr(
                runtime_events,
                attempt,
                state,
            ),
        )
    except RuntimeError as exc:
        return GitHubPrWaitResult(
            pr_number=args.pr_number,
            state=None,
            error=str(exc),
        )


def _wait_verifier(args: argparse.Namespace) -> VerifierWaitResult:
    config = VerifierWaitConfig(
        run_id=args.run_id,
        log_dir=args.log_dir,
        interval_seconds=args.interval,
        timeout_seconds=args.timeout_seconds,
    )
    runtime_events = WaitRuntimeEvents.create(
        target_kind="verifier",
        target_id=args.run_id,
    )
    return wait_for_verifier_run(
        config,
        poll_observer=lambda attempt, exists: runtime_events.polled(
            attempt=attempt,
            completed=exists,
            status="manifest-found" if exists else "manifest-missing",
        ),
    )


def _render_sweep(output_format: str, summary: SweepSummary) -> str:
    if output_format == cli_parsers.JSON_FORMAT:
        return render_sweep_json(summary)
    return render_sweep_text(summary)


def _render_cleanup(output_format: str, summary: CleanupSummary) -> str:
    if output_format == cli_parsers.JSON_FORMAT:
        return f'{{"expired_ready": {summary.expired_ready}}}'
    return f"expired ready waits: {summary.expired_ready}"


def _render_daemon_launch(output_format: str, result: daemon_launchd.DaemonLaunch) -> str:
    if output_format == cli_parsers.JSON_FORMAT:
        return json.dumps(
            {
                "started": result.started,
                "label": result.label,
                "log_path": str(result.log_path),
                "error": result.error,
            },
            sort_keys=True,
        )
    if result.started:
        return f"daemon installed: {result.label}\nlog: {result.log_path}"
    return f"daemon not started: {result.error}"


def _render_daemon_status(output_format: str, status: daemon_launchd.DaemonStatus) -> str:
    if output_format == cli_parsers.JSON_FORMAT:
        return json.dumps(
            {
                "label": status.label,
                "plist_path": str(status.plist_path),
                "log_path": str(status.log_path),
                "loaded": status.loaded,
                "pid": status.pid,
                "last_heartbeat": status.last_heartbeat,
                "error": status.error,
            },
            indent=2,
            sort_keys=True,
        )
    return daemon_launchd.status_text(status)


def _observe_github_run(
    runtime_events: WaitRuntimeEvents,
    attempt: int,
    state: GitHubRunState,
) -> None:
    """Emit compact GitHub run poll event."""

    runtime_events.polled(
        attempt=attempt,
        completed=state.completed,
        status=state.status,
        attributes={"conclusion": state.conclusion},
    )


def _observe_github_pr(
    runtime_events: WaitRuntimeEvents,
    attempt: int,
    state: GitHubPrChecksState,
) -> None:
    """Emit compact GitHub PR checks poll event."""

    runtime_events.polled(
        attempt=attempt,
        completed=state.completed,
        status="completed" if state.completed else "pending",
        attributes={
            "check_count": len(state.checks),
            "failed_count": len(state.failed_checks()),
        },
    )
