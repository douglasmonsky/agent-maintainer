"""Quiet wait command entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agent_maintainer.runtime_events.waiting import WaitRuntimeEvents
from agent_maintainer.wait.broker import (
    BackgroundGitHubPrWait,
    codex_foreground_wait_allowed,
    register_background_github_pr,
    render_background_registration_text,
    running_in_codex,
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
from agent_maintainer.wait.registry import (
    RegisterGitHubPrWait,
    WaitRecord,
    WaitRegistry,
    render_resume_text,
    render_wait_record_text,
    wait_record_json,
)
from agent_maintainer.wait.sweeper import (
    SweepSummary,
    render_sweep_json,
    render_sweep_text,
    start_wait_watcher,
    sweep_once,
    watch_wait,
)
from agent_maintainer.wait.verifier import (
    VerifierWaitConfig,
    render_verifier_wait_json,
    render_verifier_wait_text,
    wait_for_verifier_run,
)

JSON_FORMAT = "json"
TEXT_FORMAT = "text"
OUTPUT_FORMATS = (TEXT_FORMAT, JSON_FORMAT)
DEFAULT_GITHUB_INTERVAL_SECONDS = 20
DEFAULT_GITHUB_TIMEOUT_SECONDS = 3600
DEFAULT_VERIFIER_INTERVAL_SECONDS = 5
DEFAULT_VERIFIER_TIMEOUT_SECONDS = 3600


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse wait command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer wait")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_github_run_parser(subparsers)
    _add_github_pr_parser(subparsers)
    _add_verifier_parser(subparsers)
    _add_register_parser(subparsers)
    _add_resume_parser(subparsers)
    _add_sweep_parser(subparsers)
    return parser.parse_args(argv)


def _add_github_run_parser(subparsers: Any) -> None:
    """Add GitHub run wait parser."""

    github = subparsers.add_parser("github-run", help="Wait one GitHub Actions run.")
    github.add_argument("run_id")
    github.add_argument("--repo")
    github.add_argument("--interval", type=int, default=DEFAULT_GITHUB_INTERVAL_SECONDS)
    github.add_argument("--timeout-seconds", type=int, default=DEFAULT_GITHUB_TIMEOUT_SECONDS)
    github.add_argument("--format", choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_github_pr_parser(subparsers: Any) -> None:
    """Add GitHub PR wait parser."""

    github_pr = subparsers.add_parser("github-pr", help="Wait one GitHub PR check set.")
    github_pr.add_argument("pr_number")
    github_pr.add_argument("--repo")
    github_pr.add_argument("--root", type=Path, default=Path.cwd())
    github_pr.add_argument("--interval", type=int, default=DEFAULT_GITHUB_INTERVAL_SECONDS)
    github_pr.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_GITHUB_TIMEOUT_SECONDS,
    )
    github_pr.add_argument("--format", choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_verifier_parser(subparsers: Any) -> None:
    """Add verifier wait parser."""

    verifier = subparsers.add_parser("verifier", help="Wait for one verifier run.")
    verifier.add_argument("run_id")
    verifier.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    verifier.add_argument("--interval", type=int, default=DEFAULT_VERIFIER_INTERVAL_SECONDS)
    verifier.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_VERIFIER_TIMEOUT_SECONDS,
    )
    verifier.add_argument("--format", choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_register_parser(subparsers: Any) -> None:
    """Add wait registration parser."""

    register = subparsers.add_parser("register", help="Register a resumable wait.")
    register_subparsers = register.add_subparsers(
        dest="register_kind",
        required=True,
    )
    _add_register_github_pr_parser(register_subparsers)


def _add_register_github_pr_parser(subparsers: Any) -> None:
    """Add GitHub PR wait registration parser."""

    register_pr = subparsers.add_parser(
        "github-pr",
        help="Register one GitHub PR wait.",
    )
    register_pr.add_argument("pr_number")
    register_pr.add_argument("--repo")
    register_pr.add_argument("--platform", default="codex")
    register_pr.add_argument("--branch", default="")
    register_pr.add_argument("--head-sha", default="")
    register_pr.add_argument("--root", type=Path, default=Path.cwd())
    register_pr.add_argument("--start-watcher", action="store_true")
    register_pr.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_GITHUB_INTERVAL_SECONDS,
    )
    register_pr.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_GITHUB_TIMEOUT_SECONDS,
    )
    register_pr.add_argument("--format", choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_resume_parser(subparsers: Any) -> None:
    """Add wait resume parser."""

    resume = subparsers.add_parser("resume", help="Render a registered wait.")
    resume.add_argument("wait_id")
    resume.add_argument("--root", type=Path, default=Path.cwd())
    resume.add_argument("--format", choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_sweep_parser(subparsers: Any) -> None:
    """Add wait sweep parser."""

    sweep = subparsers.add_parser("sweep", help="Sweep registered waits.")
    mode = sweep.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--watch")
    sweep.add_argument("--root", type=Path, default=Path.cwd())
    sweep.add_argument("--format", choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _github_run(args: argparse.Namespace) -> int:
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
        result = wait_for_github_run(
            config,
            poll_observer=lambda attempt, state: _observe_github_run(
                runtime_events,
                attempt,
                state,
            ),
        )
    except RuntimeError as exc:
        result = GitHubWaitResult(run_id=args.run_id, state=None, error=str(exc))
    if args.format == JSON_FORMAT:
        print(render_github_wait_json(result))
    else:
        print(render_github_wait_text(result))
    return result.exit_code


def _github_pr(args: argparse.Namespace) -> int:
    if running_in_codex() and not codex_foreground_wait_allowed():
        registration = register_background_github_pr(
            BackgroundGitHubPrWait(
                root=args.root,
                pr_number=args.pr_number,
                repo=args.repo,
                interval_seconds=args.interval,
                timeout_seconds=args.timeout_seconds,
            ),
        )
        if args.format == JSON_FORMAT:
            print(wait_record_json(registration.record))
        else:
            print(render_background_registration_text(registration))
        return 0
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
        result = wait_for_github_pr_checks(
            config,
            poll_observer=lambda attempt, state: _observe_github_pr(
                runtime_events,
                attempt,
                state,
            ),
        )
    except RuntimeError as exc:
        result = GitHubPrWaitResult(
            pr_number=args.pr_number,
            state=None,
            error=str(exc),
        )
    if args.format == JSON_FORMAT:
        print(render_github_pr_wait_json(result))
    else:
        print(render_github_pr_wait_text(result))
    return result.exit_code


def _verifier_run(args: argparse.Namespace) -> int:
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
    result = wait_for_verifier_run(
        config,
        poll_observer=lambda attempt, exists: runtime_events.polled(
            attempt=attempt,
            completed=exists,
            status="manifest-found" if exists else "manifest-missing",
        ),
    )
    if args.format == JSON_FORMAT:
        print(render_verifier_wait_json(result))
    else:
        print(render_verifier_wait_text(result))
    return result.exit_code


def _register(args: argparse.Namespace) -> int:
    if args.register_kind == "github-pr":
        return _register_github_pr(args)
    return 2


def _register_github_pr(args: argparse.Namespace) -> int:
    record = WaitRegistry(args.root).register_github_pr(
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
    if args.start_watcher:
        start_wait_watcher(args.root, record.wait_id)
    print(_render_wait_record(args.format, record))
    return 0


def _resume(args: argparse.Namespace) -> int:
    record = WaitRegistry(args.root).read(args.wait_id)
    if args.format == JSON_FORMAT:
        print(wait_record_json(record))
    else:
        print(render_resume_text(record))
    return 0


def _sweep(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    if args.once:
        summary = sweep_once(registry)
        print(_render_sweep(args.format, summary))
        return 0
    record = watch_wait(registry, args.watch)
    rewake_result = CodexRewakeBackend(registry).resume_if_available(record)
    if args.format == JSON_FORMAT:
        print(wait_record_json(registry.read(record.wait_id)))
    elif codex_rewake_resumed(rewake_result):
        print(render_codex_rewake_text(record, rewake_result))
    else:
        print(render_resume_text(record))
    return 0


def _render_wait_record(output_format: str, record: WaitRecord) -> str:
    if output_format == JSON_FORMAT:
        return wait_record_json(record)
    return render_wait_record_text(record)


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
