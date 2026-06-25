#!/usr/bin/env python3
"""Codex Stop hook: run final verification before the agent finishes."""

from __future__ import annotations

import json
import subprocess  # nosec B404
import sys
from pathlib import Path

MAX_CONTEXT = 8_000


def verifier_python(repo_root: Path) -> str:
    for relative in (".venv/bin/python", "venv/bin/python"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return sys.executable


def emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload))
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    # Avoid infinite continuation loops. Codex sets this when the Stop hook
    # already continued the turn once.
    if payload.get("stop_hook_active") is True:
        return emit({"continue": True})

    repo_root = Path(__file__).resolve().parents[2]
    verifier = repo_root / "scripts" / "guardrail.py"

    if not verifier.exists():
        return emit(
            {
                "decision": "block",
                "reason": (
                    f"Repository guardrail verifier is missing at {verifier}. "
                    "Restore it before finishing."
                ),
            }
        )

    result = subprocess.run(  # nosec B603
        [
            verifier_python(repo_root),
            str(verifier),
            "verify",
            "--profile",
            "precommit",
            "--base-ref",
            "HEAD",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode == 0:
        return emit({"continue": True})

    output = (result.stdout or result.stderr or "Verification failed with no output.").strip()
    if len(output) > MAX_CONTEXT:
        output = output[:MAX_CONTEXT].rstrip() + "\n... truncated. Full logs are in .verify-logs/."

    return emit(
        {
            "decision": "block",
            "reason": (
                "Final verification failed. Fix the issues below before finishing. "
                "Do not lower thresholds or add broad suppressions.\n\n" + output
            ),
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
