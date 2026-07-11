"""CLI boundary for exact-commit release distribution bundles."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from agent_maintainer import release_artifacts_io
from agent_run_artifacts import distribution_bundle as contract
from agent_run_artifacts import git_state


def parser() -> argparse.ArgumentParser:
    """Return the release-artifact command parser."""

    root = argparse.ArgumentParser(
        prog="python -m agent_maintainer.release_artifacts",
        description="Create and verify exact-commit distribution bundles.",
    )
    subparsers = root.add_subparsers(dest="command_name", required=True)

    create = subparsers.add_parser("create", help="Create a verified bundle.")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--bundle", type=Path, required=True)
    create.add_argument("--expected-sha", required=True)
    create.set_defaults(handler=_create)

    verify = subparsers.add_parser("verify", help="Verify a transferred bundle.")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--expected-sha", required=True)
    verify.add_argument("--expected-manifest-sha256", required=True)
    verify.set_defaults(handler=_verify)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    """Run one release-artifact command and return its exit code."""

    args = parser().parse_args(argv)
    try:
        return _dispatch(args)
    except contract.DistributionBundleError as exc:
        print(f"release artifact error: {exc}", file=sys.stderr)
        return 2


def _dispatch(args: argparse.Namespace) -> int:
    handler_value: object = getattr(args, "handler", None)
    if not callable(handler_value):
        raise contract.DistributionBundleError("missing release artifact command")
    handler = cast(Callable[[argparse.Namespace], int], handler_value)
    return handler(args)


def _create(args: argparse.Namespace) -> int:
    _require_clean_checkout(args.expected_sha)
    verified = release_artifacts_io.create_distribution_bundle(
        args.source,
        args.bundle,
        expected_sha=args.expected_sha,
    )
    print(
        "distribution bundle created: "
        f"{args.bundle} ({len(verified.artifacts)} artifacts, "
        f"manifest {verified.manifest_sha256}, {args.expected_sha})"
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    _require_clean_checkout(args.expected_sha)
    verified = release_artifacts_io.verify_distribution_bundle(
        args.bundle,
        expected_sha=args.expected_sha,
        expected_manifest_sha256=args.expected_manifest_sha256,
    )
    print(
        "distribution bundle verified: "
        f"{args.bundle} ({len(verified.artifacts)} artifacts, "
        f"manifest {verified.manifest_sha256}, {args.expected_sha})"
    )
    return 0


def _require_clean_checkout(expected_sha: str) -> None:
    current = git_state.git_state(Path.cwd())
    if current.get("sha") != expected_sha:
        raise contract.DistributionBundleError("current checkout does not match expected commit")
    if current.get("dirty") is not False:
        raise contract.DistributionBundleError("current checkout is dirty")


def console_main() -> None:
    """Console entry point for module execution."""

    sys.exit(main())


if __name__ == "__main__":
    console_main()
