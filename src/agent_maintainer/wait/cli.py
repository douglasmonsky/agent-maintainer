"""Quiet wait command entrypoint."""

from __future__ import annotations

import argparse

from agent_maintainer.wait.github import (
    GitHubWaitConfig,
    GitHubWaitResult,
    render_github_wait_json,
    render_github_wait_text,
    wait_for_github_run,
)

JSON_FORMAT = "json"
TEXT_FORMAT = "text"
DEFAULT_GITHUB_INTERVAL_SECONDS = 20
DEFAULT_GITHUB_TIMEOUT_SECONDS = 3600


def main(argv: list[str] | None = None) -> int:
    """Run quiet wait subcommands."""
    args = parse_args([] if argv is None else argv)
    if args.command == "github-run":
        return _github_run(args)
    return 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse wait command arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer wait")
    subparsers = parser.add_subparsers(dest="command", required=True)
    github = subparsers.add_parser("github-run", help="Wait for one GitHub Actions run.")
    github.add_argument("run_id")
    github.add_argument("--repo")
    github.add_argument("--interval", type=int, default=DEFAULT_GITHUB_INTERVAL_SECONDS)
    github.add_argument("--timeout-seconds", type=int, default=DEFAULT_GITHUB_TIMEOUT_SECONDS)
    github.add_argument("--format", choices=(TEXT_FORMAT, JSON_FORMAT), default=TEXT_FORMAT)
    return parser.parse_args(argv)


def _github_run(args: argparse.Namespace) -> int:
    config = GitHubWaitConfig(
        run_id=args.run_id,
        repo=args.repo,
        interval_seconds=args.interval,
        timeout_seconds=args.timeout_seconds,
    )
    try:
        result = wait_for_github_run(config)
    except RuntimeError as exc:
        result = GitHubWaitResult(run_id=args.run_id, state=None, error=str(exc))
    print(_render(args.format, result))
    return result.exit_code


def _render(output_format: str, result: GitHubWaitResult) -> str:
    if output_format == JSON_FORMAT:
        return render_github_wait_json(result)
    return render_github_wait_text(result)
