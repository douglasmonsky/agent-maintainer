"""Command-line interface for agent-client hook management."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.hooks import lifecycle, manager
from agent_maintainer.hooks.pr_wait import main as pr_wait_main
from agent_maintainer.hooks.runtime import main as runtime_main

ALL_CLIENTS = manager.ALL_CLIENTS
CLIENTS = manager.CLIENTS
REPO_SCOPE = manager.REPO_SCOPE
SCOPES = manager.SCOPES
install_hooks = manager.install_hooks
selected_clients = manager.selected_clients
status_hooks = manager.status_hooks
uninstall_hooks = lifecycle.uninstall_hooks
update_hooks = lifecycle.update_hooks
CLIENT_CHOICES = (*CLIENTS, ALL_CLIENTS)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse hook-management arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer hooks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="install managed agent hooks")
    add_mutation_args(install_parser, include_async_rewake=True)

    update_parser = subparsers.add_parser("update", help="update managed agent hooks")
    add_mutation_args(update_parser, include_async_rewake=True)

    uninstall_parser = subparsers.add_parser("uninstall", help="remove managed agent hooks")
    add_mutation_args(uninstall_parser, include_async_rewake=False)

    status_parser = subparsers.add_parser("status", help="show managed hook status")
    add_common_client_args(status_parser)

    run_parser = subparsers.add_parser("run", help=argparse.SUPPRESS)
    run_parser.add_argument("--platform", required=True)
    run_parser.add_argument("--event", required=True)
    run_parser.add_argument("--profile", required=True)
    run_parser.add_argument("--repo-root", type=Path)
    run_parser.add_argument("--async-rewake", action="store_true")

    pr_wait_parser = subparsers.add_parser("pr-wait", help=argparse.SUPPRESS)
    pr_wait_parser.add_argument("--platform", required=True)
    pr_wait_parser.add_argument("--repo-root", type=Path)
    pr_wait_parser.add_argument("--async-rewake", action="store_true")

    return parser.parse_args(argv)


def add_common_client_args(parser: argparse.ArgumentParser) -> None:
    """Add target/client/scope flags to a subcommand parser."""

    parser.add_argument("client", nargs="?", default=ALL_CLIENTS, choices=CLIENT_CHOICES)
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--scope", choices=SCOPES, default=REPO_SCOPE, help="repo or user config")


def add_mutation_args(
    parser: argparse.ArgumentParser,
    *,
    include_async_rewake: bool,
) -> None:
    """Add common safe-mutation flags to a lifecycle parser."""

    add_common_client_args(parser)
    parser.add_argument("--force", action="store_true", help="resolve owned stale content")
    parser.add_argument("--yes", action="store_true", help="confirm user-scope changes")
    parser.add_argument("--dry-run", action="store_true", help="print planned changes only")
    if include_async_rewake:
        parser.add_argument(
            "--async-rewake-stop",
            action="store_true",
            help="configure Claude Code Stop/SubagentStop async rewake",
        )


def main(argv: list[str]) -> int:
    """Dispatch hook-management commands."""

    args = parse_args(argv)
    handlers = {
        "install": _install_command,
        "update": _update_command,
        "uninstall": _uninstall_command,
        "status": _status_command,
    }
    handler = handlers.get(args.command)
    if handler is None:
        return _hidden_command(args)
    return handler(args)


def install_options(args: argparse.Namespace) -> manager.InstallOptions:
    """Return install-like lifecycle options from parsed arguments."""

    return manager.InstallOptions(
        target=args.target,
        client=args.client,
        scope=args.scope,
        force=args.force,
        yes=args.yes,
        dry_run=args.dry_run,
        async_rewake_stop=args.async_rewake_stop,
    )


def _install_command(args: argparse.Namespace) -> int:
    return install_hooks(install_options(args))


def _update_command(args: argparse.Namespace) -> int:
    return update_hooks(install_options(args))


def _uninstall_command(args: argparse.Namespace) -> int:
    return uninstall_hooks(
        lifecycle.UninstallOptions(
            target=args.target,
            client=args.client,
            scope=args.scope,
            force=args.force,
            yes=args.yes,
            dry_run=args.dry_run,
        )
    )


def _status_command(args: argparse.Namespace) -> int:
    for client in selected_clients(args.client):
        status_hooks(args.target, client, args.scope)
    return 0


def _hidden_command(args: argparse.Namespace) -> int:
    if args.command == "run":
        return runtime_main(runtime_args(args))
    if args.command == "pr-wait":
        return pr_wait_main(pr_wait_args(args))
    return 1


def runtime_args(args: argparse.Namespace) -> list[str]:
    """Return hidden runtime subcommand arguments."""
    command_args = [
        "--platform",
        args.platform,
        "--event",
        args.event,
        "--profile",
        args.profile,
    ]
    add_common_run_args(command_args, args)
    return command_args


def pr_wait_args(args: argparse.Namespace) -> list[str]:
    """Return hidden PR wait hook subcommand arguments."""
    command_args = [
        "--platform",
        args.platform,
    ]
    add_common_run_args(command_args, args)
    return command_args


def add_common_run_args(command_args: list[str], args: argparse.Namespace) -> None:
    """Add repo root and async rewake flags to hidden hook commands."""
    if args.repo_root is not None:
        command_args.extend(("--repo-root", str(args.repo_root)))
    if args.async_rewake:
        command_args.append("--async-rewake")
