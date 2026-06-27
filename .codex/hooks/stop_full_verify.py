"""Codex Stop hook: run final verification before agent finishes."""

from __future__ import annotations

import importlib
import json
import os
import subprocess  # nosec B404
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

hook_audit = importlib.import_module("hook_audit")
HookAuditRecord = hook_audit.HookAuditRecord
duration_since = hook_audit.duration_since
hardened_subprocess_env = hook_audit.hardened_subprocess_env
record_hook_result = hook_audit.record_hook_result
status_for_exit = hook_audit.status_for_exit
utc_timestamp = hook_audit.utc_timestamp

MAX_CONTEXT = 8_000
HOOK_NAME = "Stop"
PROFILE = "precommit"


def verifier_python(repo_root: Path) -> str:
    """Prefer virtualenv verification."""

    for relative in (".venv/bin/python", "venv/bin/python"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return sys.executable


def verifier_env(repo_root: Path) -> dict[str, str]:
    """Return hook subprocess environment with local src package importable."""

    env = hardened_subprocess_env()
    src_path = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_path
    )
    return env


def emit(payload: dict[str, object]) -> int:
    """Emit one Codex Stop-hook response payload."""

    print(json.dumps(payload))
    return 0


def main() -> int:
    """Run precommit verification before allowing the agent to finish."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    if payload.get("stop_hook_active") is True:
        return emit({"continue": True})

    repo_root = Path(__file__).resolve().parents[2]
    verifier = repo_root / "src" / "agent_maintainer" / "__main__.py"
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
        return emit(
            {
                "decision": "block",
                "reason": (
                    f"Agent Maintainer verifier is missing at {verifier}. "
                    "Restore src/agent_maintainer before finishing."
                ),
            }
        )

    command = [
        verifier_python(repo_root),
        "-m",
        "agent_maintainer",
        "verify",
        "--profile",
        PROFILE,
        "--base-ref",
        "HEAD",
    ]
    result = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        env=verifier_env(repo_root),
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
        return emit({"continue": True})

    output = (result.stdout or result.stderr or "Verification failed with no output.").strip()
    if len(output) > MAX_CONTEXT:
        truncated_output = output[:MAX_CONTEXT].rstrip()
        output = f"{truncated_output}\n... truncated. Full logs are in .verify-logs/."
    return emit(
        {
            "decision": "block",
            "reason": (
                "Final verification failed. Fix issues below before finishing. "
                f"Do not lower thresholds or add broad suppressions.\n\n{output}"
            ),
        }
    )


if __name__ == "__main__":
    sys.exit(main())
