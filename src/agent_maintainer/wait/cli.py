"""Quiet wait command entrypoint."""

from __future__ import annotations

import argparse

from agent_maintainer.runtime_events.waiting import WaitRuntimeEvents
from agent_maintainer.wait import cli_background
from agent_maintainer.wait.cli_parsers import JSON_FORMAT, parse_args
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
from agent_maintainer.wait.registry import (
    RegisterGitHubPrWait,
    RegisterGitHubRunWait,
    RegisterVerifierWait,
    WaitRegistry,
    wait_record_json,
)
from agent_maintainer.wait.sweeper import (
    SweepSummary,
    sweep_once,
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


def main(argv: list[str] | None = None) -> int:
    """Run quiet wait subcommands."""

    args = parse_args([] if argv is None else argv)
    handlers = {
        "github-run": _github_run,
        "github-pr": _github_pr,
        "verifier": _verifier_run,
        "register": _register,
        "resume": _resume,
        "sweep": _sweep,
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
    if args.format == JSON_FORMAT:
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
    if args.format == JSON_FORMAT:
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
    if args.format == JSON_FORMAT:
        print(render_verifier_wait_json(result))
    else:
        print(render_verifier_wait_text(result))
    return result.exit_code


def _register(args: argparse.Namespace) -> int:
    if args.wait_kind == "github-pr":
        return _register_github_pr(args)
    if args.wait_kind == "github-run":
        return _register_github_run(args)
    if args.wait_kind == "verifier":
        return _register_verifier(args)
    return 2


def _register_github_pr(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    record = registry.register_github_pr(
        RegisterGitHubPrWait(
            root=args.root,
            pr_number=args.pr_number,
            repo=args.repo,
            platform=args.platform,
            branch=args.branch,
            head_sha=args.head_sha,
            interval_seconds=args.interval,
            timeout_seconds=args.timeout_seconds,
        ),
    )
    registration = cli_background.maybe_start_registered_watcher(
        args.root,
        record,
        args.start_watcher,
    )
    cli_background.emit_registered(record, background=args.start_watcher)
    print(cli_background.render_registered(args.format, record, registration))
    return 0


def _register_github_run(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    record = registry.register_github_run(
        RegisterGitHubRunWait(
            root=args.root,
            run_id=args.run_id,
            repo=args.repo,
            platform=args.platform,
            branch=args.branch,
            head_sha=args.head_sha,
            interval_seconds=args.interval,
            timeout_seconds=args.timeout_seconds,
        ),
    )
    registration = cli_background.maybe_start_registered_watcher(
        args.root,
        record,
        args.start_watcher,
    )
    cli_background.emit_registered(record, background=args.start_watcher)
    print(cli_background.render_registered(args.format, record, registration))
    return 0


def _register_verifier(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    record = registry.register_verifier(
        RegisterVerifierWait(
            root=args.root,
            run_id=args.run_id,
            platform=args.platform,
            branch=args.branch,
            head_sha=args.head_sha,
            log_dir=args.log_dir,
            interval_seconds=args.interval,
            timeout_seconds=args.timeout_seconds,
        ),
    )
    registration = cli_background.maybe_start_registered_watcher(
        args.root,
        record,
        args.start_watcher,
    )
    cli_background.emit_registered(record, background=args.start_watcher)
    print(cli_background.render_registered(args.format, record, registration))
    return 0


def _resume(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    record = registry.read(args.wait_id)
    if args.format == JSON_FORMAT:
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
    record = watch_wait(registry, args.watch)
    cli_background.emit_ready(record)
    if args.format == JSON_FORMAT:
        print(wait_record_json(record))
        return 0
    rewake = CodexRewakeBackend(registry).resume_if_available(record)
    if codex_rewake_resumed(rewake):
        cli_background.emit_resumed(record)
        print(render_codex_rewake_text(record, rewake))
        return 0
    print(cli_background.render_resume(record))
    return 0


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
    if output_format == JSON_FORMAT:
        return render_sweep_json(summary)
    return render_sweep_text(summary)


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
