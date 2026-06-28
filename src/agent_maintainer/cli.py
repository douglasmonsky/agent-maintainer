"""Canonical command-line entrypoint for repository maintenance."""

from __future__ import annotations

import sys
from collections.abc import Callable

from agent_maintainer.core.bootstrap import bootstrap, install
from agent_maintainer.core.guidance import main as guidance_main
from agent_maintainer.core.initializer import main as init_main
from agent_maintainer.core.runtime import disable_bytecode_writes
from agent_maintainer.doctor.cli import main as doctor_main
from agent_maintainer.hooks.cli import main as hooks_main
from agent_maintainer.verify.quiet import main as verify_main

disable_bytecode_writes()

CommandRunner = Callable[[list[str]], int]

USAGE = """Usage:
python -m agent_maintainer bootstrap
python -m agent_maintainer doctor [doctor options]
python -m agent_maintainer guidance [guidance options]
python -m agent_maintainer hooks [hooks options]
python -m agent_maintainer init [init options]
python -m agent_maintainer install
python -m agent_maintainer verify [verify options]

Examples:
python -m agent_maintainer bootstrap
python -m agent_maintainer doctor --strict
python -m agent_maintainer guidance
python -m agent_maintainer guidance --check
python -m agent_maintainer hooks install all
python -m agent_maintainer hooks status
python -m agent_maintainer init --track core
python -m agent_maintainer install
  python -m agent_maintainer verify --profile fast
  python -m agent_maintainer verify --profile precommit
  python -m agent_maintainer verify --profile full
  python -m agent_maintainer verify --profile manual
"""


def main(argv: list[str]) -> int:
    """Dispatch top-level maintainer command line."""

    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE.rstrip())
        status = 0
    else:
        command, *command_args = argv
        status = route_command(command, command_args)
    return status


def console_main() -> int:
    """Dispatch the installed console script."""
    return main(sys.argv[1:])


def route_command(command: str, command_args: list[str]) -> int:
    """Route one maintainer subcommand implementation."""

    handler = command_handlers().get(command)
    if handler is None:
        print(f"Unknown maintainer command: {command}", file=sys.stderr)
        print(USAGE.rstrip(), file=sys.stderr)
        return 2
    return handler(command_args)


def command_handlers() -> dict[str, CommandRunner]:
    """Return command handlers keyed by top-level subcommand name."""

    return {
        "bootstrap": bootstrap_command,
        "doctor": doctor_main,
        "guidance": guidance_main,
        "hooks": hooks_main,
        "init": init_main,
        "install": install_command,
        "verify": verify_main,
    }


def bootstrap_command(_command_args: list[str]) -> int:
    """Adapt bootstrap to the shared command handler signature."""

    return bootstrap()


def install_command(_command_args: list[str]) -> int:
    """Adapt install to the shared command handler signature."""

    return install()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
