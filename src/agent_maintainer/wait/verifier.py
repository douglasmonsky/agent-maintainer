"""Quiet waiter for local verifier run artifacts."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_maintainer.verify import async_state
from agent_maintainer.wait import verifier_rendering
from agent_maintainer.wait.verifier_manifest import (
    VerifierCheck,
    VerifierManifest,
    parse_verifier_manifest,
)
from agent_waits.models import TIMEOUT_EXIT_CODE

DEFAULT_LOG_DIR: Final = Path(".verify-logs")
DEFAULT_INTERVAL_SECONDS: Final = 5
DEFAULT_TIMEOUT_SECONDS: Final = 3600
CANCELLED_EXIT_CODE: Final = 130


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
    cancelled: bool = False
    process_exit_code: int | None = None
    error: str = ""

    @property
    def exit_code(self) -> int:
        """Return process exit code for this wait result."""
        if self.timed_out:
            return TIMEOUT_EXIT_CODE
        if self.cancelled:
            return self.process_exit_code or CANCELLED_EXIT_CODE
        if self.error:
            return 2
        if self.manifest is None:
            return 1
        return 0 if self.manifest.succeeded else 1


@dataclass(frozen=True)
class _JobStateObservation:
    """Result of checking for one durable async job record."""

    found: bool
    state: async_state.AsyncVerifierState | None = None
    error_result: VerifierWaitResult | None = None


Sleep = Callable[[int], None]
Monotonic = Callable[[], float]
VerifierPollObserver = Callable[[int, bool], None]


def wait_for_verifier_run(
    config: VerifierWaitConfig,
    *,
    sleep: Sleep = time.sleep,
    monotonic: Monotonic = time.monotonic,
    poll_observer: VerifierPollObserver | None = None,
) -> VerifierWaitResult:
    """Wait quietly until a verifier manifest exists or timeout expires."""
    started = monotonic()
    attempt = 0
    while True:
        attempt += 1
        result = query_verifier_run_once(config)
        if poll_observer is not None:
            poll_observer(attempt, result is not None)
        if result is not None:
            return result
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


def query_verifier_run_once(config: VerifierWaitConfig) -> VerifierWaitResult | None:
    """Return terminal verifier result, otherwise pending."""

    observation = _observe_job_state(config)
    if observation.found:
        return _observed_job_result(config, observation)
    manifest_path = verifier_manifest_path(config)
    if manifest_path.exists():
        return _read_manifest(config.run_id, manifest_path)
    return _read_job_result(config)


def _observed_job_result(
    config: VerifierWaitConfig,
    observation: _JobStateObservation,
) -> VerifierWaitResult | None:
    if observation.error_result is not None:
        return observation.error_result
    state = observation.state
    if state is not None and state.status == async_state.LEGACY_JOB_STATUS_STARTED:
        return _read_job_result(config)
    if state is None or not state.terminal:
        return None
    return _terminal_state_result(config, state)


def render_verifier_wait_text(result: VerifierWaitResult) -> str:
    """Render one compact verifier wait result."""

    return verifier_rendering.render_verifier_wait_text(result)


def render_verifier_wait_json(result: VerifierWaitResult) -> str:
    """Render one machine-readable verifier wait result."""

    return verifier_rendering.render_verifier_wait_json(result)


def _read_manifest(run_id: str, manifest_path: Path) -> VerifierWaitResult:
    try:
        return VerifierWaitResult(
            run_id=run_id,
            manifest=parse_verifier_manifest(manifest_path),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return VerifierWaitResult(run_id=run_id, manifest=None, error=str(exc))


def _read_job_result(config: VerifierWaitConfig) -> VerifierWaitResult | None:
    jobs_dir = config.log_dir / "jobs"
    stdout_path = jobs_dir / f"{config.run_id}.stdout.log"
    try:
        outcome = stdout_path.read_text(encoding="utf-8").strip().upper()
    except FileNotFoundError:
        return None
    except OSError as exc:
        return VerifierWaitResult(run_id=config.run_id, manifest=None, error=str(exc))
    if outcome not in {"FAIL", "PASS"}:
        return None
    profile = ""
    try:
        payload = json.loads((jobs_dir / f"{config.run_id}.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if isinstance(payload, dict):
        profile = str(payload.get("profile", ""))
    status = "passed" if outcome == "PASS" else "failed"
    return VerifierWaitResult(
        run_id=config.run_id,
        manifest=VerifierManifest(
            run_id=config.run_id,
            profile=profile,
            checks=(
                VerifierCheck(
                    name="verifier",
                    status=status,
                    log_path=str(stdout_path),
                ),
            ),
            expected_duration_hint="cached verifier result",
        ),
    )


def _observe_job_state(config: VerifierWaitConfig) -> _JobStateObservation:
    state_path = config.log_dir / "jobs" / f"{config.run_id}.json"
    try:
        state = async_state.read_async_state(state_path)
    except async_state.AsyncVerifierStateError as exc:
        return _JobStateObservation(
            found=True,
            error_result=VerifierWaitResult(
                run_id=config.run_id,
                manifest=None,
                error=str(exc),
            ),
        )
    return _JobStateObservation(found=state is not None, state=state)


def _terminal_state_result(
    config: VerifierWaitConfig,
    state: async_state.AsyncVerifierState,
) -> VerifierWaitResult:
    if state.status == async_state.JOB_STATUS_ERROR:
        detail = state.error or f"async verifier failed during {state.phase}"
        return VerifierWaitResult(
            run_id=config.run_id,
            manifest=None,
            process_exit_code=state.exit_code,
            error=detail,
        )
    if state.status == async_state.JOB_STATUS_CANCELLED:
        return VerifierWaitResult(
            run_id=config.run_id,
            manifest=None,
            cancelled=True,
            process_exit_code=state.exit_code,
            error=state.error,
        )
    state_result = _state_result(config.run_id, state)
    return _matching_manifest_result(config, state, state_result)


def _matching_manifest_result(
    config: VerifierWaitConfig,
    state: async_state.AsyncVerifierState,
    state_result: VerifierWaitResult,
) -> VerifierWaitResult:
    manifest_path = verifier_manifest_path(config)
    try:
        modified_at = manifest_path.stat().st_mtime
    except OSError:
        return state_result
    if modified_at < state.started_at:
        return state_result
    manifest_result = _read_manifest(config.run_id, manifest_path)
    if manifest_result.error or manifest_result.manifest is None:
        return state_result
    state_succeeded = state.status == async_state.JOB_STATUS_PASSED
    if manifest_result.manifest.succeeded != state_succeeded:
        return state_result
    return manifest_result


def _state_result(
    run_id: str,
    state: async_state.AsyncVerifierState,
) -> VerifierWaitResult:
    succeeded = state.status == async_state.JOB_STATUS_PASSED
    status = "passed" if succeeded else "failed"
    return VerifierWaitResult(
        run_id=run_id,
        manifest=VerifierManifest(
            run_id=run_id,
            profile=state.profile,
            checks=(
                VerifierCheck(
                    name="verifier",
                    status=status,
                    log_path=state.stdout_path,
                ),
            ),
            expected_duration_hint="detached verifier result",
        ),
    )
