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

    head = fingerprint_inputs.git_output(Path.cwd(), "rev-parse", "HEAD").strip()
    if not head:
        print("pre-push verification could not resolve HEAD", file=sys.stderr)
        return USAGE_ERROR_STATUS
    if head != to_ref:
        print(
            "pre-push verification refuses a non-HEAD local ref; "
            f"expected {to_ref}, found {head}",
            file=sys.stderr,
        )
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
