"""Parse TypeScript and JavaScript diagnostic output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import cast

TSC_DIAGNOSTIC_RE = re.compile(
    r"^(?P<path>.+?)\((?P<line>\d+),(?P<column>\d+)\): "
    r"(?P<severity>error|warning) (?P<code>TS\d+): (?P<message>.+)$"
)
JsonObject = dict[str, object]


@dataclass(frozen=True)
class TypeScriptDiagnostic:
    """One parsed TypeScript or JavaScript diagnostic."""

    path: str | None
    line: int | None
    column: int | None
    code: str | None
    message: str
    severity: str


def parse_tsc_output(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse `tsc --pretty false` diagnostics."""
    return [
        tsc_diagnostic(match)
        for line in raw_output.splitlines()
        if (match := TSC_DIAGNOSTIC_RE.match(line.strip()))
    ]


def parse_eslint_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse ESLint JSON formatter output."""
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return []
    return eslint_payload_diagnostics(payload)


def parse_jest_json(raw_output: str) -> list[TypeScriptDiagnostic]:
    """Parse Jest/Vitest-compatible JSON test output."""
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return []
    return jest_payload_diagnostics(payload) or vitest_payload_diagnostics(payload)


def eslint_payload_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from ESLint list or object payloads."""
    if isinstance(payload, dict):
        payload_object = cast(JsonObject, payload)
        return eslint_result_diagnostics(payload_object.get("results", []))
    return eslint_result_diagnostics(payload)


def eslint_result_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from ESLint result entries."""
    if not isinstance(payload, list):
        return []
    items = cast(list[object], payload)
    diagnostics: list[TypeScriptDiagnostic] = []
    for item in items:
        if isinstance(item, dict):
            result = cast(JsonObject, item)
            diagnostics.extend(
                eslint_message_diagnostic(result, message) for message in eslint_messages(result)
            )
    return diagnostics


def eslint_messages(result: JsonObject) -> list[JsonObject]:
    """Return valid ESLint message dictionaries from one result."""
    messages = result.get("messages", [])
    if not isinstance(messages, list):
        return []
    items = cast(list[object], messages)
    valid_messages: list[JsonObject] = []
    for item in items:
        if isinstance(item, dict):
            valid_messages.append(cast(JsonObject, item))
    return valid_messages


def eslint_message_diagnostic(
    result: JsonObject,
    message: JsonObject,
) -> TypeScriptDiagnostic:
    """Return one diagnostic from ESLint result plus message."""
    return TypeScriptDiagnostic(
        path=optional_text(result.get("filePath")),
        line=optional_int(message.get("line")),
        column=optional_int(message.get("column")),
        code=optional_text(message.get("ruleId")) or "eslint",
        message=str(message.get("message") or "").strip(),
        severity=eslint_severity(message.get("severity")),
    )


def jest_payload_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from Jest-compatible JSON payloads."""
    if not isinstance(payload, dict):
        return []
    payload_object = cast(JsonObject, payload)
    test_results = payload_object.get("testResults")
    if not isinstance(test_results, list):
        return []
    result_items = cast(list[object], test_results)
    diagnostics: list[TypeScriptDiagnostic] = []
    for item in result_items:
        if isinstance(item, dict):
            diagnostics.extend(jest_suite_diagnostics(cast(JsonObject, item)))
    return diagnostics


def vitest_payload_diagnostics(payload: object) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from Vitest task-style JSON payloads."""
    if not isinstance(payload, dict):
        return []
    payload_object = cast(JsonObject, payload)
    files = payload_object.get("files")
    if not isinstance(files, list):
        return []

    diagnostics: list[TypeScriptDiagnostic] = []
    for file_item in cast(list[object], files):
        if not isinstance(file_item, dict):
            continue
        file_payload = cast(JsonObject, file_item)
        diagnostics.extend(vitest_task_diagnostics(file_payload))
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
    for task_item in cast(list[object], tasks):
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
    for item in cast(list[object], value):
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


def jest_suite_diagnostics(result: JsonObject) -> list[TypeScriptDiagnostic]:
    """Return diagnostics from one Jest-compatible test suite."""
    assertions = result.get("assertionResults")
    if not isinstance(assertions, list):
        return []
    assertion_items = cast(list[object], assertions)
    diagnostics: list[TypeScriptDiagnostic] = []
    for item in assertion_items:
        if not isinstance(item, dict):
            continue
        diagnostic = jest_assertion_diagnostic(result, cast(JsonObject, item))
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def jest_assertion_diagnostic(
    result: JsonObject,
    assertion: JsonObject,
) -> TypeScriptDiagnostic | None:
    """Return one failed Jest-compatible assertion diagnostic."""
    if optional_text(assertion.get("status")) != "failed":
        return None
    line, column = jest_location(assertion.get("location"))
    return TypeScriptDiagnostic(
        path=optional_text(result.get("name")) or optional_text(result.get("testFilePath")),
        line=line,
        column=column,
        code="typescript-test",
        message=jest_failure_message(result, assertion),
        severity="error",
    )


def jest_location(value: object) -> tuple[int | None, int | None]:
    """Return optional line and column from a Jest-compatible location."""
    if not isinstance(value, dict):
        return (None, None)
    location = cast(JsonObject, value)
    return (optional_int(location.get("line")), optional_int(location.get("column")))


def jest_failure_message(result: JsonObject, assertion: JsonObject) -> str:
    """Return concise failed-test message for agent repair context."""
    test_name = jest_test_name(assertion)
    failure = first_failure_line(assertion.get("failureMessages"))
    if failure is None:
        failure = optional_text(assertion.get("failureMessage"))
    if failure is None:
        failure = optional_text(result.get("message"))
    if test_name and failure:
        return f"{test_name}: {failure}"
    return test_name or failure or "Test failed"


def jest_test_name(assertion: JsonObject) -> str | None:
    """Return best available Jest-compatible assertion name."""
    full_name = optional_text(assertion.get("fullName"))
    if full_name:
        return full_name
    title = optional_text(assertion.get("title"))
    ancestors = assertion.get("ancestorTitles")
    if isinstance(ancestors, list):
        ancestor_items = cast(list[object], ancestors)
        parts = [text for item in ancestor_items if (text := optional_text(item)) is not None]
        if title:
            parts.append(title)
        return " ".join(parts) or None
    return title


def first_failure_line(value: object) -> str | None:
    """Return first useful line from Jest-compatible failure messages."""
    if not isinstance(value, list):
        return None
    value_items = cast(list[object], value)
    for item in value_items:
        text = optional_text(item)
        if text is None:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
    return None


def tsc_diagnostic(match: re.Match[str]) -> TypeScriptDiagnostic:
    """Return one diagnostic from a TypeScript compiler regex match."""
    return TypeScriptDiagnostic(
        path=match.group("path"),
        line=int(match.group("line")),
        column=int(match.group("column")),
        code=match.group("code"),
        message=match.group("message"),
        severity=match.group("severity"),
    )


def format_diagnostic(diagnostic: TypeScriptDiagnostic) -> str:
    """Format a TypeScript diagnostic as editor-style text."""
    path = diagnostic.path or "<unknown>"
    line = diagnostic.line or 1
    column = diagnostic.column or 1
    symbol = diagnostic.code or "typescript"
    return f"{path}:{line}:{column}: {diagnostic.severity}: {symbol}: {diagnostic.message}"


def eslint_severity(value: object) -> str:
    """Return normalized ESLint severity label."""
    if value == 1:
        return "warning"
    return "error"


def optional_int(value: object) -> int | None:
    """Return integer values from diagnostic fields."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.isdecimal() else None


def optional_text(value: object) -> str | None:
    """Return stripped text when available."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
