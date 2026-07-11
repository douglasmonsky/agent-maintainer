"""Parse TypeScript and JavaScript test-runner artifacts."""

from __future__ import annotations

import json
from typing import cast

from agent_repair_facts.parsers.typescript_diagnostics import (
    JsonObject,
    TypeScriptDiagnostic,
    first_failure_line,
    jest_location,
    optional_text,
)


def parse_vitest_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse Vitest task-style JSON output."""
    try:
        payload = json.loads(raw_output)
    except (json.JSONDecodeError, RecursionError):
        return []
    return vitest_payload_diagnostics(payload)


def vitest_payload_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from Vitest task-style JSON payloads."""
    if not isinstance(payload, dict):
        return []
    files = cast(JsonObject, payload).get("files")
    if not isinstance(files, list):
        return []

    diagnostics: list[TypeScriptDiagnostic] = []
    for file_item in files:
        if not isinstance(file_item, dict):
            continue
        diagnostics.extend(vitest_task_diagnostics(cast(JsonObject, file_item)))
    return diagnostics


def vitest_task_diagnostics(file_payload: JsonObject) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from one Vitest task-style file payload."""
    file_path = (
        optional_text(file_payload.get("filepath"))
        or optional_text(file_payload.get("file"))
        or optional_text(file_payload.get("name"))
    )
    tasks = file_payload.get("tasks")
    if not isinstance(tasks, list):
        return []

    diagnostics: list[TypeScriptDiagnostic] = []
    for task_item in tasks:
        if not isinstance(task_item, dict):
            continue
        diagnostic = vitest_task_diagnostic(file_path, cast(JsonObject, task_item))
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def vitest_task_diagnostic(
    file_path: str | None,
    task: JsonObject,
) -> TypeScriptDiagnostic | None:
    """Return one failed Vitest task diagnostic."""
    result = task.get("result")
    if not isinstance(result, dict):
        return None
    result_object = cast(JsonObject, result)
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
    if not isinstance(value, list):
        return None
    for item in value:
        if isinstance(item, dict):
            return cast(JsonObject, item)
    return None


def vitest_failure_message(task: JsonObject, error: JsonObject | None) -> str:
    """Return concise failed Vitest task message."""
    test_name = optional_text(task.get("name"))
    failure = optional_text(error.get("message")) if error else None
    if failure is None and error is not None:
        failure = first_failure_line([error.get("stack")])
    if test_name and failure:
        return f"{test_name}: {failure}"
    return test_name or failure or "Test failed"
