"""Rendering helpers for generic wait records."""

from __future__ import annotations

import json

from agent_waits import constants as wait_constants
from agent_waits import models as wait_models
from agent_waits.registry import WaitRecord


def render_resume_text(record: WaitRecord) -> str:
    """Render terminal wait continuation text."""

    if not record.ready:
        return render_wait_record_text(record)
    message = record.resume_message or render_wait_record_text(record)
    return "\n".join((message, "", "Continuation:", _continuation_prompt(record)))


def render_wait_record_text(record: WaitRecord) -> str:
    """Render compact wait record state."""

    result = record.terminal_result or wait_constants.RESULT_PENDING
    details = (
        f"kind: {record.kind}",
        f"target: {record.target_id}",
        f"status: {record.status}",
    )
    return wait_models.render_wait_capsule(
        wait_models.WaitRepairCapsule(
            result=result,
            run_id=record.wait_id,
            details=details,
            likely_next_action=record.resume_instruction if record.ready else "",
        ),
    )


def wait_record_json(record: WaitRecord) -> str:
    """Render wait record stable JSON."""

    return json.dumps(record.as_dict(), indent=2, sort_keys=True)


def _continuation_prompt(record: WaitRecord) -> str:
    if record.kind == "github-pr":
        return (
            f"PR checks reached {record.terminal_result} for PR #{record.target_id}. "
            "Review PR diff, inspect failures if any, merge only if satisfactory, "
            "then continue the prior roadmap task."
        )
    if record.kind == "github-run":
        return (
            f"GitHub run {record.target_id} reached {record.terminal_result}. "
            "Inspect failed jobs if any, repair and rerun only what is needed, "
            "then continue the prior task."
        )
    if record.kind == "verifier":
        return (
            f"Verifier run {record.target_id} reached {record.terminal_result}. "
            "Inspect failed checks if any, repair the branch, and continue the prior task."
        )
    return (
        f"Wait {record.wait_id} reached {record.terminal_result}. "
        "Inspect failures if any, take the appropriate follow-up, "
        "and continue the prior task."
    )
