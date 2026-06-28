"""Command-line interface for agent-client hook management."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.hooks.manager import (
    ALL_CLIENTS,
    CLIENTS,
    REPO_SCOPE,
    SCOPES,
    InstallOptions,
    install_hooks,
    selected_clients,
    status_hooks,
)
from agent_maintainer.hooks.runtime import main as runtime_main

CLIENT_CHOICES = (*CLIENTS, ALL_CLIENTS)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse hook-management arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer hooks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="install managed agent hooks")
    add_common_client_args(install_parser)
    install_parser.add_argument("--force", action="store_true", help="overwrite after backing up")
    install_parser.add_argument("--yes", action="store_true", help="confirm user-scope writes")
    install_parser.add_argument("--dry-run", action="store_true", help="print planned writes only")

    status_parser = subparsers.add_parser("status", help="show managed hook status")
    add_common_client_args(status_parser)

    run_parser = subparsers.add_parser("run", help=argparse.SUPPRESS)
    run_parser.add_argument("--platform", required=True)
    run_parser.add_argument("--event", required=True)
    run_parser.add_argument("--profile", required=True)
    run_parser.add_argument("--repo-root", type=Path)

    return parser.parse_args(argv)


def add_common_client_args(parser: argparse.ArgumentParser) -> None:
    """Add target/client/scope flags to a subcommand parser."""

    parser.add_argument("client", nargs="?", default=ALL_CLIENTS, choices=CLIENT_CHOICES)
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--scope", choices=SCOPES, default=REPO_SCOPE, help="repo or user config")


def main(argv: list[str]) -> int:
    """Dispatch hook-management commands."""

    args = parse_args(argv)
    if args.command == "install":
        return install_hooks(
            InstallOptions(
                target=args.target,
                client=args.client,
                scope=args.scope,
                force=args.force,
                yes=args.yes,
                dry_run=args.dry_run,
            )
        )
    if args.command == "status":
        for client in selected_clients(args.client):
            status_hooks(args.target, client, args.scope)
        return 0
    if args.command == "run":
        runtime_args = [
            "--platform",
            args.platform,
            "--event",
            args.event,
            "--profile",
            args.profile,
        ]
        if args.repo_root is not None:
            runtime_args.extend(("--repo-root", str(args.repo_root)))
        return runtime_main(runtime_args)
    return 1
