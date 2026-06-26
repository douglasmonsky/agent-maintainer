#!/usr/bin/env python3
"""Codex PostToolUse hook: run fast checks after file edits.

PostToolUse cannot undo an edit; it feeds concise failure context back into the
agent so the next step is repair instead of continued drift.
"""

from __future__ import annotations

import importlib
import json
import subprocess  # nosec B404
import sys
import time
from contextlib import suppress
from pathlib import Path

sys.dont_write_bytecode = True

hook_audit = importlib.import_module("hook_audit")
HookAuditRecord = hook_audit.HookAuditRecord
duration_since = hook_audit.duration_since
hardened_subprocess_env = hook_audit.hardened_subprocess_env
record_hook_result = hook_audit.record_hook_result
status_for_exit = hook_audit.status_for_exit
utc_timestamp = hook_audit.utc_timestamp

MAX_CONTEXT = 6_000
HOOK_NAME = "PostToolUse"
PROFILE = "fast"


def verifier_python(repo_root: Path) -> str:
    """Prefer the repository virtualenv when running the verifier."""

    for relative in (".venv/bin/python", "venv/bin/python"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return sys.executable


def emit_block(reason: str, additional_context: str) -> int:
    """Emit a Codex PostToolUse block decision with concise repair context."""

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
    """Run fast guardrails after edits and block only when repair is needed."""

    with suppress(json.JSONDecodeError):
        json.load(sys.stdin)

    repo_root = Path(__file__).resolve().parents[2]
    verifier = repo_root / "scripts" / "guardrail.py"
    started_at = utc_timestamp()
    started = time.monotonic()

    if not verifier.exists():
        record_hook_result(
            repo_root,
            HookAuditRecord(
                hook_name=HOOK_NAME,
                profile=PROFILE,
                status="failed",
                command=(),
                exit_code=None,
                started_at=started_at,
                ended_at=utc_timestamp(),
                duration_seconds=duration_since(started),
                reason="missing verifier",
            ),
        )
        return emit_block(
            "Repository guardrail verifier is missing.",
            f"Expected verifier at {verifier}. Restore scripts/guardrail.py before continuing.",
        )

    command = [
        verifier_python(repo_root),
        "-m",
        "scripts.guardrail",
        "verify",
        "--profile",
        PROFILE,
        "--base-ref",
        "HEAD",
    ]
    result = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        env=hardened_subprocess_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    record_hook_result(
        repo_root,
        HookAuditRecord(
            hook_name=HOOK_NAME,
            profile=PROFILE,
            status=status_for_exit(result.returncode),
            command=tuple(command),
            exit_code=result.returncode,
            started_at=started_at,
            ended_at=utc_timestamp(),
            duration_seconds=duration_since(started),
        ),
    )

    if result.returncode == 0:
        return 0

    output = (result.stdout or result.stderr or "Verification failed with no output.").strip()
    if len(output) > MAX_CONTEXT:
        truncated_output = output[:MAX_CONTEXT].rstrip()
        output = f"{truncated_output}\n... truncated. Full logs are in .verify-logs/."

    return emit_block(
        "Fast repository guardrails failed after a file edit.",
        (
            "Repair these issues before continuing. Do not suppress the checks unless the "
            f"suppression is narrow and justified.\n\n{output}"
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
