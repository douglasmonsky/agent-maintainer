"""Wait registration CLI handlers."""

from __future__ import annotations

import argparse

from agent_maintainer.wait import cli_background
from agent_maintainer.wait.git_context import complete_git_identity
from agent_maintainer.wait.registry import (
    RegisterGitHubPrWait,
    RegisterGitHubRunWait,
    RegisterVerifierWait,
    WaitRecord,
    WaitRegistry,
)


def register_wait(args: argparse.Namespace) -> int:
    """Register one background wait from parsed CLI arguments."""

    if args.wait_kind == "github-pr":
        return _register_github_pr(args)
    if args.wait_kind == "github-run":
        return _register_github_run(args)
    if args.wait_kind == "verifier":
        return _register_verifier(args)
    return 2


def _register_github_pr(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    branch, head_sha = complete_git_identity(
        args.root,
        branch=args.branch,
        head_sha=args.head_sha,
    )
    record = registry.register_github_pr(
        RegisterGitHubPrWait(
            root=args.root,
            pr_number=args.pr_number,
            repo=args.repo,
            platform=args.platform,
            branch=branch,
            head_sha=head_sha,
            interval_seconds=args.interval,
            timeout_seconds=args.timeout_seconds,
        ),
    )
    return _emit_registration(args, record)


def _register_github_run(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    branch, head_sha = complete_git_identity(
        args.root,
        branch=args.branch,
        head_sha=args.head_sha,
    )
    record = registry.register_github_run(
        RegisterGitHubRunWait(
            root=args.root,
            run_id=args.run_id,
            repo=args.repo,
            platform=args.platform,
            branch=branch,
            head_sha=head_sha,
            interval_seconds=args.interval,
            timeout_seconds=args.timeout_seconds,
        ),
    )
    return _emit_registration(args, record)


def _register_verifier(args: argparse.Namespace) -> int:
    registry = WaitRegistry(args.root)
    branch, head_sha = complete_git_identity(
        args.root,
        branch=args.branch,
        head_sha=args.head_sha,
    )
    record = registry.register_verifier(
        RegisterVerifierWait(
            root=args.root,
            run_id=args.run_id,
            platform=args.platform,
            branch=branch,
            head_sha=head_sha,
            log_dir=args.log_dir,
            interval_seconds=args.interval,
            timeout_seconds=args.timeout_seconds,
        ),
    )
    return _emit_registration(args, record)


def _emit_registration(args: argparse.Namespace, record: WaitRecord) -> int:
    registration = cli_background.maybe_start_registered_watcher(
        args.root,
        record,
        args.start_watcher,
    )
    cli_background.emit_registered(record, background=args.start_watcher)
    print(cli_background.render_registered(args.format, record, registration))
    return 0
