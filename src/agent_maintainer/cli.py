"""Canonical command-line entrypoint for repository maintenance."""

from __future__ import annotations

import sys
from collections.abc import Callable

from agent_maintainer.context.cli import main as context_main
from agent_maintainer.core.bootstrap import bootstrap, install
from agent_maintainer.core.guidance import main as guidance_main
from agent_maintainer.core.runtime import disable_bytecode_writes
from agent_maintainer.core.scaffold.initializer import main as init_main
from agent_maintainer.doctor.cli import main as doctor_main
from agent_maintainer.hooks.cli import main as hooks_main
from agent_maintainer.runtime_events.commands import run_with_command_events
from agent_maintainer.verify.quiet import main as verify_main

disable_bytecode_writes()

CommandRunner = Callable[[list[str]], int]

# docsync:evidence.start evidence.readme.command_registry
USAGE = """Usage:
  python -m agent_maintainer <command> [options]

Core commands:
  attention       Build and inspect local file attention ledgers.
  assess          Recommend setup and score maintenance debt.
  bootstrap       Install development dependencies for this checkout.
  doctor          Inspect setup health and configuration drift.
  events        Summarize local runtime event JSONL artifacts.
  guidance        Generate or check AGENTS.agent-maintainer.md.
  init            Write starter files into a target repository.
  install         Install local hooks for this repository.
  mcp             Run optional typed MCP tool surface.
  wait            Wait quietly for long-running external work.
  verify          Run configured verification profiles.

Agent repair commands:
  change-plan     Manage cohesive change plans.
  context         Read bounded failure, log, file, and diff context.
  ratchet         Inspect legacy-ratchet baselines and repair targets.
  repair-plan     Generate repair guidance from current diagnostics.
  scoring         Manage local scoring dataset examples.
  test-intel      Suggest relevant tests and deeper test targets.

Operations:
  hooks           Install, audit, and inspect agent-client hooks.
  report          Render diagnostic reports.

Examples:
  python -m agent_maintainer doctor --strict
  python -m agent_maintainer assess setup
  python -m agent_maintainer assess debt
  python -m agent_maintainer assess file-baselines
  python -m agent_maintainer verify --profile precommit
  python -m agent_maintainer verify --profile full
  python -m agent_maintainer context failures
  python -m agent_maintainer context log pyright --tail 120
  python -m agent_maintainer guidance --check
  python -m agent_maintainer hooks status
  python -m agent_maintainer events summary
  python -m agent_maintainer scoring examples export --format jsonl
  python -m agent_maintainer wait github-run <run-id>
  python -m agent_maintainer report html
"""


def main(argv: list[str]) -> int:
    """Dispatch top-level maintainer command line."""

    return run_with_command_events(
        argv,
        lambda: _dispatch(argv),
        known_commands=command_handlers(),
    )


def _dispatch(argv: list[str]) -> int:
    """Dispatch top-level maintainer command line without event instrumentation."""

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
        "attention": attention_command,
        "assess": assess_command,
        "bootstrap": bootstrap_command,
        "change-plan": change_plan_command,
        "context": context_main,
        "doctor": doctor_main,
        "events": events_command,
        "guidance": guidance_main,
        "hooks": hooks_main,
        "init": init_main,
        "install": install_command,
        "mcp": mcp_command,
        "ratchet": ratchet_command,
        "report": report_command,
        "repair-plan": repair_plan_command,
        "scoring": scoring_command,
        "test-intel": test_intel_command,
        "wait": wait_command,
        "verify": verify_main,
    }


# docsync:evidence.end evidence.readme.command_registry


def assess_command(command_args: list[str]) -> int:
    """Run assess command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.assess.cli", command_args)


def attention_command(command_args: list[str]) -> int:
    """Run attention command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.attention.cli", command_args)


def bootstrap_command(_command_args: list[str]) -> int:
    """Adapt bootstrap shared command handler signature."""
    return bootstrap()


def change_plan_command(command_args: list[str]) -> int:
    """Run change-plan command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.change_plan.cli", command_args)


def events_command(command_args: list[str]) -> int:
    """Run runtime events command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.runtime_events.cli", command_args)


def install_command(_command_args: list[str]) -> int:
    """Adapt install shared command handler signature."""
    return install()


def mcp_command(command_args: list[str]) -> int:
    """Run optional MCP server command lazily."""
    return _run_module_main("agent_maintainer.mcp.server", command_args)


def ratchet_command(command_args: list[str]) -> int:
    """Run ratchet command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.ratchet.cli", command_args)


def report_command(command_args: list[str]) -> int:
    """Run report command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.report.cli", command_args)


def repair_plan_command(command_args: list[str]) -> int:
    """Run repair-plan command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.repair_plan.cli", command_args)


def scoring_command(command_args: list[str]) -> int:
    """Run scoring command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.scoring.cli", command_args)


def test_intel_command(command_args: list[str]) -> int:
    """Run test-intel command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.test_intel.cli", command_args)


def wait_command(command_args: list[str]) -> int:
    """Run quiet wait command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.wait.cli", command_args)


def _run_module_main(module_name: str, command_args: list[str]) -> int:
    """Import one command module and run its main function."""
    module = __import__(module_name, fromlist=("main",))
    return module.main(command_args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
