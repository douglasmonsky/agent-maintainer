"""Parse TypeScript and JavaScript test-runner artifacts."""

from __future__ import annotations

import json

from agent_repair_facts.parsers.typescript_diagnostics import (
    JsonObject,
    TypeScriptDiagnostic,
    first_failure_line,
    jest_location,
    optional_text,
)
from agent_repair_facts.payloads import json_object, json_objects


def parse_vitest_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse Vitest task-style JSON output."""
    try:
        payload = json.loads(raw_output)
    except (json.JSONDecodeError, RecursionError):
        return []
    return vitest_payload_diagnostics(payload)


def vitest_payload_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from Vitest task-style JSON payloads."""
    payload_object = json_object(payload)
    if payload_object is None:
        return []
    files = json_objects(payload_object.get("files"))

    diagnostics: list[TypeScriptDiagnostic] = []
    for file_item in files:
        diagnostics.extend(vitest_task_diagnostics(file_item))
    return diagnostics


def vitest_task_diagnostics(file_payload: JsonObject) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from one Vitest task-style file payload."""
    file_path = (
        optional_text(file_payload.get("filepath"))
        or optional_text(file_payload.get("file"))
        or optional_text(file_payload.get("name"))
    )
    tasks = json_objects(file_payload.get("tasks"))

    diagnostics: list[TypeScriptDiagnostic] = []
    for task_item in tasks:
        diagnostic = vitest_task_diagnostic(file_path, task_item)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def vitest_task_diagnostic(
    file_path: str | None,
    task: JsonObject,
) -> TypeScriptDiagnostic | None:
    """Return one failed Vitest task diagnostic."""
    result_object = json_object(task.get("result"))
    if result_object is None:
        return None
    state = optional_text(result_object.get("state"))
    if state not in {"fail", "failed"}:
        return None
    error = first_error_object(result_object.get("errors"))
    line, column = jest_location(error.get("location") if error else None)
    return TypeScriptDiagnostic(
        path=file_path,
        line=line,
        column=column,
        code="typescript-test",
        message=vitest_failure_message(task, error),
        severity="error",
    )


def first_error_object(value: object) -> JsonObject | None:
    """Return first object from an errors list."""
    objects = json_objects(value)
    return objects[0] if objects else None


def vitest_failure_message(task: JsonObject, error: JsonObject | None) -> str:
    """Return concise failed Vitest task message."""
    test_name = optional_text(task.get("name"))
    failure = optional_text(error.get("message")) if error else None
    if failure is None and error is not None:
        failure = first_failure_line([error.get("stack")])
    if test_name and failure:
        return f"{test_name}: {failure}"
    return test_name or failure or "Test failed"
