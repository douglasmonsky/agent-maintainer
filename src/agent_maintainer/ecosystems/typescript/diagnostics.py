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
