"""Background registration helpers for the wait CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.runtime_events import waiting as wait_runtime
from agent_maintainer.wait import broker
from agent_maintainer.wait.handlers import handler_for
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry, wait_record_json
from agent_maintainer.wait.sweeper import SweepSummary
from agent_waits.notifications import (
    claim_fallback_used_observation,
    claim_registration_observation,
    claim_terminal_observation,
    claim_watcher_started_observation,
)
from agent_waits.watcher_state import watcher_state

JSON_FORMAT = "json"


def background_github_pr_if_needed(
    args: argparse.Namespace,
) -> broker.BackgroundWaitRegistration | None:
    """Convert Codex foreground PR wait into background registration."""

    if (
        broker.running_in_codex()
        and broker.codex_background_pr_wait_enabled()
        and not broker.codex_foreground_wait_allowed()
    ):
        registration = broker.register_background_github_pr(
            broker.BackgroundGitHubPrWait(
                root=args.root,
                pr_number=args.pr_number,
                repo=args.repo,
                interval_seconds=args.interval,
                timeout_seconds=args.timeout_seconds,
            ),
        )
        emit_registered(args.root, registration.record, background=True)
        emit_watcher_result(args.root, registration)
        emit_fallback_handoff(args.root, registration, output_format=args.format)
        emit_foreground_blocked(registration.record)
        return registration
    return None


def background_github_run_if_needed(
    args: argparse.Namespace,
) -> broker.BackgroundWaitRegistration | None:
    """Convert Codex foreground GitHub run wait into background registration."""

    if known_wait_should_background():
        registration = broker.register_background_github_run(
            broker.BackgroundGitHubRunWait(
                root=args.root,
                run_id=args.run_id,
                repo=args.repo,
                interval_seconds=args.interval,
                timeout_seconds=args.timeout_seconds,
            ),
        )
        emit_registered(args.root, registration.record, background=True)
        emit_watcher_result(args.root, registration)
        emit_fallback_handoff(args.root, registration, output_format=args.format)
        emit_foreground_blocked(registration.record)
        return registration
    return None


def background_verifier_if_needed(
    args: argparse.Namespace,
) -> broker.BackgroundWaitRegistration | None:
    """Convert Codex foreground verifier wait into background registration."""

    if known_wait_should_background():
        registration = broker.register_background_verifier(
            broker.BackgroundVerifierWait(
                root=args.root,
                run_id=args.run_id,
                log_dir=args.log_dir,
                interval_seconds=args.interval,
                timeout_seconds=args.timeout_seconds,
            ),
        )
        emit_registered(args.root, registration.record, background=True)
        emit_watcher_result(args.root, registration)
        emit_fallback_handoff(args.root, registration, output_format=args.format)
        emit_foreground_blocked(registration.record)
        return registration
    return None


def known_wait_should_background() -> bool:
    """Return whether known wait commands should background in Codex."""

    return (
        broker.running_in_codex()
        and broker.codex_background_wait_enabled()
        and not broker.codex_foreground_wait_allowed()
    )


def maybe_start_registered_watcher(
    root: Path,
    record: WaitRecord,
    start_watcher: bool,
) -> broker.BackgroundWaitRegistration | None:
    """Start watcher for an explicitly registered wait when requested."""

    if not start_watcher:
        return None
    return broker.start_registered_watcher(root, record)


def emit_registered(root: Path, record: WaitRecord, *, background: bool) -> None:
    """Claim and emit a wait registration runtime event once."""

    observed = claim_registration_observation(WaitRegistry(root), record.wait_id)
    if observed is not None:
        wait_events(observed).registered(wait_id=observed.wait_id, background=background)


def emit_foreground_blocked(record: WaitRecord) -> None:
    """Emit a Codex foreground wait blocked runtime event."""

    wait_events(record).foreground_blocked(wait_id=record.wait_id)


def emit_swept(summary: SweepSummary) -> None:
    """Emit a wait sweep runtime event."""

    wait_runtime.WaitRuntimeEvents.create(
        target_kind="wait-registry",
        target_id="wait-sweep",
    ).swept(
        checked=summary.checked,
        updated=summary.updated,
        pending=summary.pending,
        ready=summary.ready,
    )


def emit_ready(registry: WaitRegistry, record: WaitRecord) -> None:
    """Claim and emit a terminal wait-ready runtime event once."""

    observed = claim_terminal_observation(registry, record.wait_id)
    if observed is None:
        return
    wait_events(observed).ready(
        wait_id=observed.wait_id,
        result=observed.terminal_result,
    )


def emit_resumed(record: WaitRecord) -> None:
    """Emit an automatic wait-resume runtime event."""

    wait_events(record).resumed(wait_id=record.wait_id)


def emit_watcher_result(
    root: Path,
    registration: broker.BackgroundWaitRegistration,
) -> None:
    """Emit one privacy-safe watcher lifecycle result."""

    record = registration.record
    events = wait_events(record)
    state = watcher_state(record)
    if registration.watcher_started:
        observed = claim_watcher_started_observation(WaitRegistry(root), record.wait_id)
        if observed is not None:
            wait_runtime.emit_watcher_started(
                events,
                wait_id=record.wait_id,
                strategy=state.strategy,
            )
    elif state.error_code:
        wait_runtime.emit_watcher_failed(
            events,
            wait_id=record.wait_id,
            reason=state.error_code,
        )


def emit_fallback_handoff(
    root: Path,
    registration: broker.BackgroundWaitRegistration,
    *,
    output_format: str,
) -> None:
    """Emit one fallback event only when the text handoff exposes it."""

    if output_format == JSON_FORMAT or broker.codex_terminal_rewake_available(registration):
        return
    observed = claim_fallback_used_observation(
        WaitRegistry(root),
        registration.record.wait_id,
    )
    if observed is None:
        return
    backoff = broker.heartbeat_backoff(registration.record)
    wait_runtime.emit_fallback_used(
        wait_events(registration.record),
        wait_id=registration.record.wait_id,
        initial_interval_seconds=int(backoff["initial_interval_seconds"]),
        max_interval_seconds=int(backoff["max_interval_seconds"]),
    )


def render_registered(
    output_format: str,
    record: WaitRecord,
    registration: broker.BackgroundWaitRegistration | None,
) -> str:
    """Render explicit wait registration output."""

    if output_format == JSON_FORMAT:
        return wait_record_json(record)
    if registration is not None:
        return broker.render_background_registration_text(registration)
    return render_resume(record)


def render_resume(record: WaitRecord) -> str:
    """Render manual resume output for one wait record."""

    return handler_for(record.kind).render_resume(record)


def render_background(
    output_format: str,
    registration: broker.BackgroundWaitRegistration,
) -> str:
    """Render implicit background registration output."""

    if output_format == JSON_FORMAT:
        return wait_record_json(registration.record)
    return broker.render_background_registration_text(registration)


def wait_events(record: WaitRecord) -> wait_runtime.WaitRuntimeEvents:
    """Return runtime event adapter for one wait record."""

    return wait_runtime.WaitRuntimeEvents.create(
        target_kind=record.kind,
        target_id=record.target_id,
    )
