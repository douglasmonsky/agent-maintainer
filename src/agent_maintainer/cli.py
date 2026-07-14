"""Canonical command-line entrypoint for repository maintenance."""

from __future__ import annotations

import sys

from agent_maintainer.config import preflight
from agent_maintainer.context.cli import main as _context_main
from agent_maintainer.core.guidance import main as _guidance_main
from agent_maintainer.core.runtime import disable_bytecode_writes
from agent_maintainer.core.scaffold.initializer import main as _init_main
from agent_maintainer.doctor.cli import main as _doctor_main
from agent_maintainer.hooks.cli import main as _hooks_main
from agent_maintainer.runtime_events.commands import run_with_command_events
from agent_maintainer.skill.cli import main as _skill_main
from agent_maintainer.verify.quiet import main as _verify_main

disable_bytecode_writes()

CommandRunner = preflight.CommandRunner


context_main: CommandRunner = preflight.ValidatedCommand(_context_main)
guidance_main: CommandRunner = preflight.ValidatedCommand(_guidance_main)
init_main: CommandRunner = preflight.ValidatedCommand(_init_main)
doctor_main: CommandRunner = preflight.ValidatedCommand(_doctor_main)
hooks_main: CommandRunner = preflight.ValidatedCommand(_hooks_main)
verify_main: CommandRunner = preflight.ValidatedCommand(_verify_main)

# docsync:evidence.start evidence.readme.command_registry
USAGE = """Usage:
  python -m agent_maintainer <command> [options]

Stable workflows:
  doctor          Inspect setup health and configuration drift.
  guidance        Generate or check AGENTS.agent-maintainer.md.
  init            Write starter files into a target repository.
  install         Install local hooks for this repository.
  skill           Install the setup skill for personal agent clients.
  verify          Run configured verification profiles.
  wait            Quiet polling is stable; terminal rewake is experimental.

Repair and inspection:
  assess          Recommend setup and score maintenance debt.
  context         Read bounded failure, log, file, and diff context.
  ratchet         Inspect legacy-ratchet baselines and repair targets.
  repair-plan     Generate repair guidance from current diagnostics.
  test-intel      Suggest relevant tests and deeper test targets.

Optional local intelligence:
  attention       Build and inspect local file attention ledgers.
  events          Summarize local runtime event JSONL artifacts.
  report          Render diagnostic reports.
  scoring         Manage local scoring dataset examples.

Experimental integrations:
  mcp             Run optional typed MCP tool surface.

Operations:
  bootstrap       Install development dependencies for this checkout.
  change-plan     Manage cohesive change plans.
  hooks           Install, audit, and inspect agent-client hooks.

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
  python -m agent_maintainer skill install --client codex --client claude-code
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
        "skill": skill_command,
        "test-intel": test_intel_command,
        "wait": wait_command,
        "verify": verify_main,
    }


# docsync:evidence.end evidence.readme.command_registry


@preflight.ValidatedCommand
def assess_command(command_args: list[str]) -> int:
    """Run assess command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.assess.cli", command_args)


@preflight.ValidatedCommand
def attention_command(command_args: list[str]) -> int:
    """Run attention command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.attention.cli", command_args)


@preflight.ValidatedCommand
def bootstrap_command(command_args: list[str]) -> int:
    """Adapt bootstrap shared command handler signature."""
    return _run_module_main("agent_maintainer.core.setup_cli", ["bootstrap", *command_args])


@preflight.ValidatedCommand
def change_plan_command(command_args: list[str]) -> int:
    """Run change-plan command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.change_plan.cli", command_args)


@preflight.ValidatedCommand
def events_command(command_args: list[str]) -> int:
    """Run runtime events command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.runtime_events.cli", command_args)


@preflight.ValidatedCommand
def install_command(command_args: list[str]) -> int:
    """Adapt install shared command handler signature."""
    return _run_module_main("agent_maintainer.core.setup_cli", ["install", *command_args])


@preflight.ValidatedCommand
def mcp_command(command_args: list[str]) -> int:
    """Run optional MCP server command lazily."""
    return _run_module_main("agent_maintainer.mcp.server", command_args)


@preflight.ValidatedCommand
def ratchet_command(command_args: list[str]) -> int:
    """Run ratchet command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.ratchet.cli", command_args)


@preflight.ValidatedCommand
def report_command(command_args: list[str]) -> int:
    """Run report command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.report.cli", command_args)


@preflight.ValidatedCommand
def repair_plan_command(command_args: list[str]) -> int:
    """Run repair-plan command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.repair_plan.cli", command_args)


@preflight.ValidatedCommand
def scoring_command(command_args: list[str]) -> int:
    """Run scoring command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.scoring.cli", command_args)


def skill_command(command_args: list[str]) -> int:
    """Manage personal setup skills without repository configuration preflight."""
    return _skill_main(command_args)


@preflight.ValidatedCommand
def test_intel_command(command_args: list[str]) -> int:
    """Run test-intel command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.test_intel.cli", command_args)


@preflight.ValidatedCommand
def wait_command(command_args: list[str]) -> int:
    """Run quiet wait command lazily to keep entrypoint light."""
    return _run_module_main("agent_maintainer.wait.cli", command_args)


def _run_module_main(module_name: str, command_args: list[str]) -> int:
    """Import one command module and run its main function."""
    module = __import__(module_name, fromlist=("main",))
    return module.main(command_args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
