#!/usr/bin/env python3
"""Codex PostToolUse hook: run fast checks after file edits.

PostToolUse cannot undo an edit; it feeds concise failure context back into the
agent so the next step is repair instead of continued drift.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MAX_CONTEXT = 6_000


def verifier_python(repo_root: Path) -> str:
    for relative in (".venv/bin/python", "venv/bin/python"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return sys.executable


def emit_block(reason: str, additional_context: str) -> int:
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": additional_context,
                },
            }
        )
    )
    return 0


def main() -> int:
    try:
        _payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        _payload = {}

    repo_root = Path(__file__).resolve().parents[2]
    verifier = repo_root / "scripts" / "verify_quiet.py"

    if not verifier.exists():
        return emit_block(
            "Repository guardrail verifier is missing.",
            f"Expected verifier at {verifier}. Restore scripts/verify_quiet.py before continuing.",
        )

    result = subprocess.run(
        [verifier_python(repo_root), str(verifier), "--profile", "fast", "--base-ref", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )

    if result.returncode == 0:
        return 0

    output = (result.stdout or result.stderr or "Verification failed with no output.").strip()
    if len(output) > MAX_CONTEXT:
        output = output[:MAX_CONTEXT].rstrip() + "\n... truncated. Full logs are in .verify-logs/."

    return emit_block(
        "Fast repository guardrails failed after a file edit.",
        (
            "Repair these issues before continuing. Do not suppress the checks unless the "
            "suppression is narrow and justified.\n\n" + output
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
