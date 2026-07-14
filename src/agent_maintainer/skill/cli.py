"""Manage the portable Agent Maintainer setup skill for personal clients."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.skill import lifecycle


def main(argv: list[str] | None = None) -> int:
    """Parse and dispatch personal skill lifecycle commands."""
    args = parse_args(argv or [])
    try:
        statuses = _dispatch(args)
    except lifecycle.SkillOwnershipError as exc:
        print(exc, file=sys.stderr)
        return 1
    for status_value in statuses:
        print(_render_status(status_value))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Return the setup-skill argument contract."""
    parser = argparse.ArgumentParser(prog="agent-maintainer skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install or update the setup skill.")
    _add_clients(install_parser, required=True)

    status_parser = subparsers.add_parser("status", help="Inspect setup skill ownership.")
    _add_clients(status_parser, required=False)

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Remove unmodified files owned by the setup skill.",
    )
    _add_clients(uninstall_parser, required=True)
    return parser.parse_args(argv)


def user_home() -> Path:
    """Return the home directory that owns personal client configuration."""
    return Path.home()


def _add_clients(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument(
        "--client",
        action="append",
        choices=lifecycle.CLIENTS,
        required=required,
        dest="clients",
        help="Personal client to manage; repeat to select both.",
    )


def _dispatch(args: argparse.Namespace) -> tuple[lifecycle.SkillStatus, ...]:
    home = user_home()
    clients = tuple(args.clients or lifecycle.CLIENTS)
    if args.command == "install":
        return lifecycle.install(home, clients)
    if args.command == "uninstall":
        return lifecycle.uninstall(home, clients)
    return tuple(lifecycle.status(home, client) for client in clients)


def _render_status(status_value: lifecycle.SkillStatus) -> str:
    state = status_value.state.value
    fields = [
        f"{status_value.client}: {state}",
        f"packaged={status_value.package_version}",
    ]
    if status_value.installed_version is not None:
        fields.append(f"installed={status_value.installed_version}")
    fields.append(f"path={status_value.destination}")
    if status_value.detail:
        fields.append(f"detail={status_value.detail}")
    return "; ".join(fields)
