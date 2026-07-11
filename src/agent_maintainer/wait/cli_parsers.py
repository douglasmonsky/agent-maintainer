"""Argument parser helpers for the wait CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agent_maintainer.wait.verifier import DEFAULT_LOG_DIR

JSON_FORMAT = "json"
TEXT_FORMAT = "text"
OUTPUT_FORMATS = (TEXT_FORMAT, JSON_FORMAT)
ROOT_OPTION = "--root"
FORMAT_OPTION = "--format"
DEFAULT_GITHUB_INTERVAL_SECONDS = 20
DEFAULT_GITHUB_TIMEOUT_SECONDS = 3600
DEFAULT_VERIFIER_INTERVAL_SECONDS = 5
DEFAULT_VERIFIER_TIMEOUT_SECONDS = 3600
DEFAULT_READY_CLEANUP_SECONDS = 7 * 24 * 60 * 60
DEFAULT_DAEMON_INTERVAL_SECONDS = 5
DEFAULT_DAEMON_IDLE_TIMEOUT_SECONDS = 1800
DEFAULT_CODEX_SMOKE_TIMEOUT_SECONDS = 30.0


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
    _add_heartbeat_parser(subparsers)
    _add_cleanup_parser(subparsers)
    _add_codex_smoke_parser(subparsers)
    _add_daemon_parser(subparsers)
    return parser.parse_args(argv)


def _add_github_run_parser(subparsers: Any) -> None:
    """Add GitHub run wait parser."""

    github = subparsers.add_parser("github-run", help="Wait one GitHub run.")
    github.add_argument("run_id")
    github.add_argument("--repo")
    github.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    github.add_argument("--interval", type=int, default=DEFAULT_GITHUB_INTERVAL_SECONDS)
    github.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_GITHUB_TIMEOUT_SECONDS,
    )
    github.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_github_pr_parser(subparsers: Any) -> None:
    """Add GitHub PR checks wait parser."""

    github_pr = subparsers.add_parser(
        "github-pr",
        help="Wait one GitHub PR check set.",
    )
    github_pr.add_argument("pr_number")
    github_pr.add_argument("--repo")
    github_pr.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    github_pr.add_argument("--interval", type=int, default=DEFAULT_GITHUB_INTERVAL_SECONDS)
    github_pr.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_GITHUB_TIMEOUT_SECONDS,
    )
    github_pr.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_verifier_parser(subparsers: Any) -> None:
    """Add verifier wait parser."""

    verifier = subparsers.add_parser("verifier", help="Wait for one verifier run.")
    verifier.add_argument("run_id")
    verifier.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    verifier.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    verifier.add_argument("--interval", type=int, default=DEFAULT_VERIFIER_INTERVAL_SECONDS)
    verifier.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_VERIFIER_TIMEOUT_SECONDS,
    )
    verifier.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_register_parser(subparsers: Any) -> None:
    """Add wait register parser."""

    register = subparsers.add_parser("register", help="Register background wait.")
    register_subparsers = register.add_subparsers(dest="wait_kind", required=True)
    _add_register_github_pr_parser(register_subparsers)
    _add_register_github_run_parser(register_subparsers)
    _add_register_verifier_parser(register_subparsers)


def _add_register_github_pr_parser(subparsers: Any) -> None:
    """Add GitHub PR register parser."""

    register_pr = subparsers.add_parser(
        "github-pr",
        help="Register one GitHub PR wait.",
    )
    register_pr.add_argument("pr_number")
    _add_common_register_args(register_pr)
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
    register_pr.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_register_github_run_parser(subparsers: Any) -> None:
    """Add GitHub run register parser."""

    register_run = subparsers.add_parser(
        "github-run",
        help="Register one GitHub run wait.",
    )
    register_run.add_argument("run_id")
    _add_common_register_args(register_run)
    register_run.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_GITHUB_INTERVAL_SECONDS,
    )
    register_run.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_GITHUB_TIMEOUT_SECONDS,
    )
    register_run.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_register_verifier_parser(subparsers: Any) -> None:
    """Add verifier register parser."""

    register_verifier = subparsers.add_parser(
        "verifier",
        help="Register one verifier wait.",
    )
    register_verifier.add_argument("run_id")
    register_verifier.add_argument("--platform", default="codex")
    register_verifier.add_argument("--branch", default="")
    register_verifier.add_argument("--head-sha", default="")
    register_verifier.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    register_verifier.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    register_verifier.add_argument("--start-watcher", action="store_true")
    register_verifier.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_VERIFIER_INTERVAL_SECONDS,
    )
    register_verifier.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_VERIFIER_TIMEOUT_SECONDS,
    )
    register_verifier.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_common_register_args(parser: Any) -> None:
    parser.add_argument("--repo")
    parser.add_argument("--platform", default="codex")
    parser.add_argument("--branch", default="")
    parser.add_argument("--head-sha", default="")
    parser.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    parser.add_argument("--start-watcher", action="store_true")


def _add_resume_parser(subparsers: Any) -> None:
    """Add wait resume parser."""

    resume = subparsers.add_parser("resume", help="Render registered wait.")
    resume.add_argument("wait_id")
    resume.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    resume.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_sweep_parser(subparsers: Any) -> None:
    """Add wait sweep parser."""

    sweep = subparsers.add_parser("sweep", help="Sweep registered waits.")
    mode = sweep.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--one")
    mode.add_argument("--watch")
    sweep.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    sweep.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_heartbeat_parser(subparsers: Any) -> None:
    """Add repo-level wait heartbeat parser."""

    heartbeat = subparsers.add_parser(
        "heartbeat",
        help="Sweep once and print ready wait resumptions only.",
    )
    heartbeat.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())


def _add_cleanup_parser(subparsers: Any) -> None:
    """Add wait cleanup parser."""

    cleanup = subparsers.add_parser(
        "cleanup",
        help="Expire stale ready wait records.",
    )
    cleanup.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    cleanup.add_argument(
        "--ready-older-than-seconds",
        type=int,
        default=DEFAULT_READY_CLEANUP_SECONDS,
    )
    cleanup.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_codex_smoke_parser(subparsers: Any) -> None:
    """Add explicit Codex app-server smoke parser."""

    smoke = subparsers.add_parser(
        "codex-smoke",
        help="Probe Codex app-server; real turn requires an environment gate.",
    )
    smoke.add_argument("--start-turn", action="store_true")
    smoke.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_CODEX_SMOKE_TIMEOUT_SECONDS,
    )
    smoke.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)


def _add_daemon_parser(subparsers: Any) -> None:
    """Add repo-scoped wait daemon parser."""

    daemon = subparsers.add_parser("daemon", help="Manage repo wait daemon.")
    daemon_subparsers = daemon.add_subparsers(dest="daemon_command", required=True)

    install = daemon_subparsers.add_parser("install", help="Install LaunchAgent.")
    _add_common_daemon_args(install)
    install.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)

    uninstall = daemon_subparsers.add_parser("uninstall", help="Remove LaunchAgent.")
    uninstall.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    uninstall.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)

    status = daemon_subparsers.add_parser("status", help="Inspect LaunchAgent.")
    status.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    status.add_argument(FORMAT_OPTION, choices=OUTPUT_FORMATS, default=TEXT_FORMAT)

    run = daemon_subparsers.add_parser("run", help="Run daemon loop.")
    _add_common_daemon_args(run)


def _add_common_daemon_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(ROOT_OPTION, type=Path, default=Path.cwd())
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_DAEMON_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=DEFAULT_DAEMON_IDLE_TIMEOUT_SECONDS,
    )
