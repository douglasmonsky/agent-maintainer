"""CLI boundary for exact-commit release evidence."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from agent_maintainer import release_evidence_io
from agent_run_artifacts import git_state
from agent_run_artifacts import release_evidence as contracts

MAX_MANIFEST_BYTES = release_evidence_io.MAX_MANIFEST_BYTES


def parser() -> argparse.ArgumentParser:
    """Return the release-evidence command parser."""

    root = argparse.ArgumentParser(
        prog="python -m agent_maintainer.release_evidence",
        description="Aggregate and validate exact-commit release evidence.",
    )
    subparsers = root.add_subparsers(dest="command_name", required=True)

    aggregate = subparsers.add_parser(
        "aggregate",
        help="Aggregate all required profile manifests.",
    )
    aggregate.add_argument("--expected-sha", required=True)
    aggregate.add_argument("--manifest", action="append", type=Path, required=True)
    aggregate.add_argument("--output", type=Path, required=True)
    aggregate.set_defaults(handler=_aggregate)

    validate = subparsers.add_parser(
        "validate",
        help="Validate self-contained release evidence.",
    )
    validate.add_argument("--expected-sha", required=True)
    validate.add_argument("--manifest", type=Path, required=True)
    validate.set_defaults(handler=_validate)

    record = subparsers.add_parser(
        "record",
        help="Run and record the release-only profile command.",
    )
    record.add_argument("--output", type=Path, required=True)
    record.add_argument("profile_command", nargs=argparse.REMAINDER)
    record.set_defaults(handler=_record)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    """Run one release-evidence command and return its exit code."""

    args = parser().parse_args(argv)
    try:
        return _dispatch(args)
    except contracts.ReleaseEvidenceError as exc:
        print(f"release evidence error: {exc}", file=sys.stderr)
        return 2


def _dispatch(args: argparse.Namespace) -> int:
    handler_value: object = getattr(args, "handler", None)
    if not callable(handler_value):
        raise contracts.ReleaseEvidenceError("missing release evidence command")
    handler = cast(Callable[[argparse.Namespace], int], handler_value)
    return handler(args)


def _aggregate(args: argparse.Namespace) -> int:
    _require_clean_checkout(args.expected_sha)
    manifests = [release_evidence_io.read_payload(path) for path in args.manifest]
    evidence = contracts.aggregate_profile_manifests(
        manifests,
        expected_sha=args.expected_sha,
    )
    release_evidence_io.write_payload(args.output, evidence)
    print(
        "release evidence aggregated: "
        f"{args.output} ({len(contracts.REQUIRED_PROFILES)} profiles, {args.expected_sha})"
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    _require_clean_checkout(args.expected_sha)
    evidence = release_evidence_io.read_payload(args.manifest)
    contracts.validate_release_evidence(
        evidence,
        expected_sha=args.expected_sha,
    )
    print(f"release evidence valid: {args.manifest} ({args.expected_sha})")
    return 0


def _record(args: argparse.Namespace) -> int:
    command = _profile_command(args.profile_command)
    started_at = datetime.now(UTC)
    completed = subprocess.run(  # nosec B603
        list(command),
        cwd=Path.cwd(),
        check=False,
    )
    ended_at = datetime.now(UTC)
    manifest = contracts.command_profile_manifest(
        contracts.CommandProfileRun(
            profile="release",
            command=command,
            exit_code=completed.returncode,
            git=git_state.git_state(Path.cwd()),
            started_at=started_at,
            ended_at=ended_at,
        )
    )
    release_evidence_io.write_payload(args.output, manifest)
    print(f"release profile recorded: {args.output} (exit {completed.returncode})")
    return completed.returncode


def _profile_command(raw_command: Sequence[str]) -> tuple[str, ...]:
    command = tuple(raw_command)
    if command[:1] == ("--",):
        command = command[1:]
    if not command:
        raise contracts.ReleaseEvidenceError("record requires a command after --")
    return command


def _require_clean_checkout(expected_sha: str) -> None:
    current = git_state.git_state(Path.cwd())
    if current.get("sha") != expected_sha:
        raise contracts.ReleaseEvidenceError("current checkout does not match expected commit")
    if current.get("dirty") is not False:
        raise contracts.ReleaseEvidenceError("current checkout is dirty")


def console_main() -> None:
    """Console entry point for module execution."""

    sys.exit(main())


if __name__ == "__main__":
    console_main()
