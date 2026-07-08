"""Follow-through metrics for local agent efficacy reports."""

from __future__ import annotations

from typing import Any

from agent_maintainer.assess.efficacy_models import (
    UNKNOWN,
    EfficacyMetric,
)

PASS_STATUSES = frozenset(("pass", "passed", "success"))
POINTER_COMMANDS = frozenset(("context", "repair-plan"))
WAIT_BACKGROUND_STATUSES = frozenset(("background",))


def metrics(records: list[dict[str, Any]]) -> list[EfficacyMetric]:
    """Return pointer, repair-loop, and wait-helper metrics."""

    failure_count = _event_count(records, "check.failed")
    return [
        _pointer_metric(records, failure_count),
        EfficacyMetric(
            name="context_pack_expansions",
            value=_command_count(records, "context"),
            unit="commands",
            kind="measured",
            detail="completed context commands observed in runtime events",
        ),
        _repair_success_metric(records, failure_count),
        _wait_metric(records),
        *_background_wait_metrics(records),
        _manual_escalation_metric(records, failure_count),
    ]


def _event_count(records: list[dict[str, Any]], event_name: str) -> int:
    return sum(1 for record in records if record.get("event_name") == event_name)


def _command_count(
    records: list[dict[str, Any]],
    command: str,
    *,
    status: str | None = None,
) -> int:
    return sum(1 for record in records if _is_command(record, command, status=status))


def _pointer_metric(
    records: list[dict[str, Any]],
    failure_count: int,
) -> EfficacyMetric:
    pointer_count = sum(_command_count(records, command) for command in POINTER_COMMANDS)
    return EfficacyMetric(
        name="pointer_follow_through_rate",
        value=_percentage(pointer_count, failure_count),
        unit="percent",
        kind="estimated" if failure_count else UNKNOWN,
        detail="context or repair-plan commands after check failures",
        numerator=pointer_count if failure_count else None,
        denominator=failure_count if failure_count else None,
    )


def _repair_success_metric(
    records: list[dict[str, Any]],
    failure_count: int,
) -> EfficacyMetric:
    repair_successes = _repair_success_count(records)
    return EfficacyMetric(
        name="repair_next_action_success_rate",
        value=_percentage(repair_successes, failure_count),
        unit="percent",
        kind="estimated" if failure_count else UNKNOWN,
        detail="failed checks later followed by a passing check event",
        numerator=repair_successes if failure_count else None,
        denominator=failure_count if failure_count else None,
    )


def _wait_metric(records: list[dict[str, Any]]) -> EfficacyMetric:
    wait_total = _command_count(records, "wait")
    wait_passes = _command_count(records, "wait", status="pass")
    return EfficacyMetric(
        name="wait_helper_success_rate",
        value=_percentage(wait_passes, wait_total),
        unit="percent",
        kind="measured" if wait_total else UNKNOWN,
        detail="wait command passes divided by all wait command completions",
        numerator=wait_passes if wait_total else None,
        denominator=wait_total if wait_total else None,
    )


def _background_wait_metrics(records: list[dict[str, Any]]) -> list[EfficacyMetric]:
    registrations = _events(records, "wait.registered")
    registration_count = len(registrations)
    background_count = sum(
        1 for record in registrations if _is_background_wait_registration(record)
    )
    ready_count = _event_count(records, "wait.ready")
    claimed_count = _event_count(records, "wait.terminal_claimed")

    return [
        EfficacyMetric(
            name="background_wait_registration_rate",
            value=_percentage(background_count, registration_count),
            unit="percent",
            kind="measured" if registration_count else UNKNOWN,
            detail="background wait.registered events divided by wait.registered events",
            numerator=background_count if registration_count else None,
            denominator=registration_count if registration_count else None,
        ),
        EfficacyMetric(
            name="foreground_wait_blocked_count",
            value=_event_count(records, "wait.foreground_blocked"),
            unit="events",
            kind="measured",
            detail="foreground wait commands converted to background handoffs",
        ),
        EfficacyMetric(
            name="wait_heartbeat_noop_count",
            value=_event_count(records, "wait.heartbeat_noop"),
            unit="events",
            kind="measured",
            detail="heartbeat sweeps that found no terminal wait output",
        ),
        EfficacyMetric(
            name="wait_terminal_claim_rate",
            value=_percentage(claimed_count, ready_count),
            unit="percent",
            kind="measured" if ready_count else UNKNOWN,
            detail="terminal wait claims divided by wait.ready events",
            numerator=claimed_count if ready_count else None,
            denominator=ready_count if ready_count else None,
        ),
    ]


def _manual_escalation_metric(
    records: list[dict[str, Any]],
    failure_count: int,
) -> EfficacyMetric:
    """Return manual escalation rate from explicit runtime events."""

    escalation_count = _event_count(records, "manual.escalation")
    return EfficacyMetric(
        name="manual_escalation_rate",
        value=_percentage(escalation_count, failure_count),
        unit="percent",
        kind="measured" if failure_count else UNKNOWN,
        detail="manual.escalation events divided by check failures",
        numerator=escalation_count if failure_count else None,
        denominator=failure_count if failure_count else None,
    )


def _events(records: list[dict[str, Any]], event_name: str) -> list[dict[str, Any]]:
    return [record for record in records if record.get("event_name") == event_name]


def _is_background_wait_registration(record: dict[str, Any]) -> bool:
    if record.get("status") in WAIT_BACKGROUND_STATUSES:
        return True

    attributes = record.get("attributes")
    return isinstance(attributes, dict) and attributes.get("background") is True


def _is_command(record: dict[str, Any], command: str, *, status: str | None) -> bool:
    return (
        record.get("event_name") == "command.finished"
        and record.get("command") == command
        and (status is None or record.get("status") == status)
    )


def _percentage(numerator: int, denominator: int) -> float | str:
    if denominator <= 0:
        return UNKNOWN
    return round((numerator / denominator) * 100, 1)


def _repair_success_count(records: list[dict[str, Any]]) -> int:
    successes = 0
    for index, record in enumerate(records):
        check = record.get("check")
        if record.get("event_name") != "check.failed" or not isinstance(check, str):
            continue
        if any(_passing_check(candidate, check) for candidate in records[index + 1 :]):
            successes += 1
    return successes


def _passing_check(record: dict[str, Any], check: str) -> bool:
    return (
        record.get("event_name") == "check.finished"
        and record.get("check") == check
        and record.get("status") in PASS_STATUSES
    )
