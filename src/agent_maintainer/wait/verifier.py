"""Quiet waiter for local verifier run artifacts."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_maintainer.wait.models import (
    TIMEOUT_EXIT_CODE,
    WaitRepairCapsule,
    render_wait_capsule,
)
from agent_maintainer.wait.verifier_manifest import (
    VerifierCheck,
    VerifierManifest,
    parse_verifier_manifest,
)

DEFAULT_LOG_DIR: Final = Path(".verify-logs")
DEFAULT_INTERVAL_SECONDS: Final = 5
DEFAULT_TIMEOUT_SECONDS: Final = 3600
ONE_MINUTE_SECONDS: Final = 60


@dataclass(frozen=True)
class VerifierWaitConfig:
    """Inputs for waiting on one local verifier run."""

    run_id: str
    log_dir: Path = DEFAULT_LOG_DIR
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class VerifierWaitResult:
    """Final local verifier wait result."""

    run_id: str
    manifest: VerifierManifest | None
    timed_out: bool = False
    error: str = ""

    @property
    def exit_code(self) -> int:
        """Return process exit code for this wait result."""
        if self.timed_out:
            return TIMEOUT_EXIT_CODE
        if self.error:
            return 2
        if self.manifest is None:
            return 1
        return 0 if self.manifest.succeeded else 1


Sleep = Callable[[int], None]
Monotonic = Callable[[], float]


def wait_for_verifier_run(
    config: VerifierWaitConfig,
    *,
    sleep: Sleep = time.sleep,
    monotonic: Monotonic = time.monotonic,
) -> VerifierWaitResult:
    """Wait quietly until a verifier manifest exists or timeout expires."""
    started = monotonic()
    manifest_path = verifier_manifest_path(config)
    while True:
        if manifest_path.exists():
            return _read_manifest(config.run_id, manifest_path)
        if monotonic() - started >= config.timeout_seconds:
            return VerifierWaitResult(
                run_id=config.run_id,
                manifest=None,
                timed_out=True,
            )
        sleep(config.interval_seconds)


def verifier_manifest_path(config: VerifierWaitConfig) -> Path:
    """Return manifest path for one verifier run id."""
    return config.log_dir / "runs" / config.run_id / "manifest.json"


def render_verifier_wait_text(result: VerifierWaitResult) -> str:
    """Render one compact verifier wait result."""
    if result.error:
        return _render_error(result)
    if result.timed_out:
        return _render_timeout(result)
    manifest = result.manifest
    if manifest is None:
        return render_wait_capsule(
            WaitRepairCapsule(result="UNKNOWN", run_id=result.run_id),
        )
    if manifest.succeeded:
        return _render_success(manifest)
    return _render_failure(manifest)


def render_verifier_wait_json(result: VerifierWaitResult) -> str:
    """Render verifier wait result as JSON."""
    payload: dict[str, object] = {
        "run_id": result.run_id,
        "timed_out": result.timed_out,
        "error": result.error,
        "exit_code": result.exit_code,
    }
    if result.manifest is not None:
        payload["profile"] = result.manifest.profile
        payload["status"] = "passed" if result.manifest.succeeded else "failed"
        payload["failed_checks"] = [check.name for check in result.manifest.failed_checks]
    return json.dumps(payload, indent=2, sort_keys=True)


def _read_manifest(run_id: str, manifest_path: Path) -> VerifierWaitResult:
    try:
        return VerifierWaitResult(
            run_id=run_id,
            manifest=parse_verifier_manifest(manifest_path),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return VerifierWaitResult(run_id=run_id, manifest=None, error=str(exc))


def _render_success(manifest: VerifierManifest) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="PASS",
            profile=manifest.profile,
            run_id=manifest.run_id,
            details=_manifest_details(manifest),
        ),
    )


def _render_failure(manifest: VerifierManifest) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="FAIL",
            profile=manifest.profile,
            run_id=manifest.run_id,
            details=_manifest_details(manifest),
            top_repair_facts=_failure_facts(manifest.failed_checks),
            likely_next_action=_likely_next_action(manifest.failed_checks),
            expand_command=_expand_command(manifest),
        ),
    )


def _render_error(result: VerifierWaitResult) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="ERROR",
            run_id=result.run_id,
            details=(result.error,),
            likely_next_action=f"python -m agent_maintainer wait verifier {result.run_id}",
        ),
    )


def _render_timeout(result: VerifierWaitResult) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="TIMEOUT",
            run_id=result.run_id,
            likely_next_action=f"python -m agent_maintainer wait verifier {result.run_id}",
        ),
    )


def _manifest_details(manifest: VerifierManifest) -> tuple[str, ...]:
    details: list[str] = []
    if manifest.duration_seconds is not None:
        details.append(f"Duration: {_format_duration(manifest.duration_seconds)}")
    if manifest.expected_duration_hint:
        details.append(f"Expected duration: {manifest.expected_duration_hint}")
    return tuple(details)


def _failure_facts(failed_checks: tuple[VerifierCheck, ...]) -> tuple[str, ...]:
    if not failed_checks:
        return ("Verifier: no failed checks reported in manifest",)
    return tuple(_failure_fact(check) for check in failed_checks)


def _failure_fact(check: VerifierCheck) -> str:
    fact = f"{check.name}: {check.status}"
    if check.log_path:
        return f"{fact} ({check.log_path})"
    return fact


def _likely_next_action(failed_checks: tuple[VerifierCheck, ...]) -> str:
    for check in failed_checks:
        if check.expansion_commands:
            return check.expansion_commands[0]
    return "Inspect the first failed verifier check."


def _expand_command(manifest: VerifierManifest) -> str:
    if manifest.failure_snapshot:
        return manifest.failure_snapshot
    return (
        "python -m agent_maintainer context "
        f"--log-dir .verify-logs/runs/{manifest.run_id} failures --limit 20"
    )


def _format_duration(seconds: float) -> str:
    if seconds < ONE_MINUTE_SECONDS:
        return f"{seconds:.1f}s"
    minutes = int(seconds // ONE_MINUTE_SECONDS)
    remaining = int(seconds % ONE_MINUTE_SECONDS)
    return f"{minutes}m {remaining}s"
