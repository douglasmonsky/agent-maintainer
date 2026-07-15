"""Run complete verification against the exact outgoing Git range."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from agent_maintainer.verify import fingerprint_inputs
from agent_maintainer.verify.quiet import main as verify_main

FROM_REF_ENV = "PRE_COMMIT_FROM_REF"
TO_REF_ENV = "PRE_COMMIT_TO_REF"
USAGE_ERROR_STATUS = 2
Verifier = Callable[[list[str]], int]


def run_pre_push(
    environ: Mapping[str, str],
    *,
    verifier: Verifier = verify_main,
) -> int:
    """Verify the commits between pre-commit's remote and local push refs."""

    from_ref = environ.get(FROM_REF_ENV, "").strip()
    to_ref = environ.get(TO_REF_ENV, "").strip()
    if not from_ref or not to_ref:
        print(
            "pre-push verification requires PRE_COMMIT_FROM_REF and "
            "PRE_COMMIT_TO_REF; run through an installed pre-push hook",
            file=sys.stderr,
        )
        return USAGE_ERROR_STATUS

    repo_root = Path.cwd()
    head_output = fingerprint_inputs.git_output_checked(repo_root, "rev-parse", "HEAD")
    if head_output is None or not head_output.strip():
        print("pre-push verification could not resolve HEAD", file=sys.stderr)
        return USAGE_ERROR_STATUS
    head = head_output.strip()
    if head != to_ref:
        print(
            f"pre-push verification refuses a non-HEAD local ref; expected {to_ref}, found {head}",
            file=sys.stderr,
        )
        return USAGE_ERROR_STATUS

    status = fingerprint_inputs.git_output_checked(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status is None or status.strip():
        message = (
            "pre-push verification could not inspect checkout state"
            if status is None
            else (
                "pre-push verification requires a clean checkout so uncommitted state "
                "cannot contaminate the outgoing commit range"
            )
        )
        print(message, file=sys.stderr)
        return USAGE_ERROR_STATUS

    return verifier(
        [
            "--profile",
            "precommit",
            "--base-ref",
            from_ref,
            "--compare-branch",
            from_ref,
        ]
    )


def main() -> int:
    """Run the installed pre-push verification entrypoint."""

    return run_pre_push(os.environ)


if __name__ == "__main__":
    sys.exit(main())
