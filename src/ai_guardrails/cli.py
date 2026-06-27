"""Canonical command-line entrypoint for repository guardrails."""

from __future__ import annotations

import sys
from collections.abc import Callable

from ai_guardrails.core.bootstrap import bootstrap, install
from ai_guardrails.core.guidance import main as guidance_main
from ai_guardrails.core.initializer import main as init_main
from ai_guardrails.core.runtime import disable_bytecode_writes
from ai_guardrails.doctor.cli import main as doctor_main
from ai_guardrails.verify.quiet import main as verify_main

disable_bytecode_writes()

CommandRunner = Callable[[list[str]], int]

USAGE = """Usage:
python -m ai_guardrails bootstrap
python -m ai_guardrails doctor [doctor options]
python -m ai_guardrails guidance [guidance options]
python -m ai_guardrails init [init options]
python -m ai_guardrails install
python -m ai_guardrails verify [verify options]

Examples:
python -m ai_guardrails bootstrap
python -m ai_guardrails doctor --strict
python -m ai_guardrails guidance
python -m ai_guardrails guidance --check
python -m ai_guardrails init --track core
python -m ai_guardrails install
  python -m ai_guardrails verify --profile fast
  python -m ai_guardrails verify --profile precommit
  python -m ai_guardrails verify --profile full
  python -m ai_guardrails verify --profile manual
"""


def main(argv: list[str]) -> int:
    """Dispatch top-level guardrail command line."""

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
    """Route one guardrail subcommand implementation."""

    handler = command_handlers().get(command)
    if handler is None:
        print(f"Unknown guardrail command: {command}", file=sys.stderr)
        print(USAGE.rstrip(), file=sys.stderr)
        return 2
    return handler(command_args)


def command_handlers() -> dict[str, CommandRunner]:
    """Return command handlers keyed by top-level subcommand name."""

    return {
        "bootstrap": bootstrap_command,
        "doctor": doctor_main,
        "guidance": guidance_main,
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
