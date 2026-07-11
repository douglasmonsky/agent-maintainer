"""Compact text and JSON rendering for terminal verifier waits."""

from __future__ import annotations

import json
from typing import Final, Protocol, cast

from agent_maintainer.wait.verifier_manifest import VerifierCheck, VerifierManifest
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

ONE_MINUTE_SECONDS: Final = 60


class VerifierWaitResultLike(Protocol):
    """Terminal verifier result surface required by renderers."""

    @property
    def run_id(self) -> str:
        """Return verifier run id."""

        raise NotImplementedError

    @property
    def manifest(self) -> VerifierManifest | None:
        """Return parsed verifier manifest, when available."""

        raise NotImplementedError

    @property
    def timed_out(self) -> bool:
        """Return whether the wait expired."""

        raise NotImplementedError

    @property
    def cancelled(self) -> bool:
        """Return whether the child was cancelled."""

        raise NotImplementedError

    @property
    def error(self) -> str:
        """Return infrastructure error detail."""

        raise NotImplementedError

    @property
    def process_exit_code(self) -> int | None:
        """Return the detached child's terminal exit status."""

        raise NotImplementedError

    @property
    def exit_code(self) -> int:
        """Return the terminal process status."""

        raise NotImplementedError


def render_verifier_wait_text(result: VerifierWaitResultLike) -> str:
    """Render one compact verifier wait result."""

    special_result = _special_result_text(result)
    if special_result is not None:
        return special_result
    manifest = cast("VerifierManifest", result.manifest)
    if manifest.succeeded:
        return _render_success(manifest)
    return _render_failure(manifest)


def render_verifier_wait_json(result: VerifierWaitResultLike) -> str:
    """Render verifier wait result as JSON."""

    payload: dict[str, object] = {
        "run_id": result.run_id,
        "timed_out": result.timed_out,
        "cancelled": result.cancelled,
        "error": result.error,
        "exit_code": result.exit_code,
        "process_exit_code": result.process_exit_code,
    }
    if result.manifest is not None:
        payload["profile"] = result.manifest.profile
        payload["status"] = "passed" if result.manifest.succeeded else "failed"
        payload["failed_checks"] = [check.name for check in result.manifest.failed_checks]
    elif result.cancelled:
        payload["status"] = "cancelled"
    elif result.error:
        payload["status"] = "error"
    elif result.timed_out:
        payload["status"] = "timed_out"
    return json.dumps(payload, indent=2, sort_keys=True)


def _special_result_text(result: VerifierWaitResultLike) -> str | None:
    if result.cancelled:
        return _render_cancelled(result)
    if result.error:
        return _render_error(result)
    if result.timed_out:
        return _render_timeout(result)
    if result.manifest is None:
        return render_wait_capsule(
            WaitRepairCapsule(result="UNKNOWN", run_id=result.run_id),
        )
    return None


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


def _render_error(result: VerifierWaitResultLike) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="ERROR",
            run_id=result.run_id,
            details=(result.error,),
            likely_next_action=f"python -m agent_maintainer wait verifier {result.run_id}",
        ),
    )


def _render_cancelled(result: VerifierWaitResultLike) -> str:
    return render_wait_capsule(
        WaitRepairCapsule(
            result="CANCELLED",
            run_id=result.run_id,
            details=(result.error,) if result.error else (),
            likely_next_action="python -m agent_maintainer verify --force",
        ),
    )


def _render_timeout(result: VerifierWaitResultLike) -> str:
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
