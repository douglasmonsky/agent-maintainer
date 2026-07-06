"""Local runtime event export contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent_maintainer.runtime_events.read import RuntimeEventReadResult, RuntimeEventSource

JSONL_FORMAT = "jsonl"
OTEL_JSON_FORMAT = "otel-json"
EXPORT_FORMATS = (JSONL_FORMAT, OTEL_JSON_FORMAT)
RecordSource = tuple[dict[str, Any], RuntimeEventSource | None]


@dataclass(frozen=True)
class RuntimeEventExport:
    """Rendered local runtime event export payload."""

    format: str
    text: str


def export_runtime_events(
    read_result: RuntimeEventReadResult,
    *,
    output_format: str,
) -> RuntimeEventExport:
    """Return a local export representation without network side effects."""
    if output_format == JSONL_FORMAT:
        return RuntimeEventExport(format=output_format, text=_export_jsonl(read_result))
    if output_format == OTEL_JSON_FORMAT:
        return RuntimeEventExport(format=output_format, text=_export_otel_json(read_result))
    raise ValueError(f"unknown runtime event export format: {output_format}")


def _export_jsonl(read_result: RuntimeEventReadResult) -> str:
    rows = [
        json.dumps(_record_with_source(record, source), sort_keys=True)
        for record, source in _records_with_sources(read_result)
    ]
    if not rows:
        return ""
    body = "\n".join(rows)
    return f"{body}\n"


def _export_otel_json(read_result: RuntimeEventReadResult) -> str:
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "agent-maintainer"}},
                        {"key": "telemetry.source", "value": {"stringValue": "local-jsonl"}},
                    ],
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "agent_maintainer.runtime_events"},
                        "spans": [
                            _otel_span(record, source)
                            for record, source in _records_with_sources(read_result)
                        ],
                    },
                ],
            },
        ],
    }
    body = json.dumps(payload, indent=2, sort_keys=True)
    return f"{body}\n"


def _records_with_sources(
    read_result: RuntimeEventReadResult,
) -> list[RecordSource]:
    sources: list[RuntimeEventSource | None] = list(read_result.sources)
    if len(sources) < len(read_result.records):
        sources.extend(None for _index in range(len(read_result.records) - len(sources)))
    return list(zip(read_result.records, sources, strict=False))


def _record_with_source(
    record: dict[str, Any],
    source: RuntimeEventSource | None,
) -> dict[str, Any]:
    if source is None:
        return dict(record)
    return {
        **record,
        "source_file": source.file,
        "source_line": source.line,
    }


def _otel_span(record: dict[str, Any], source: RuntimeEventSource | None) -> dict[str, Any]:
    attributes = [
        {"key": key, "value": _otel_value(value)}
        for key, value in sorted(record.items())
        if key != "timestamp"
    ]
    if source is not None:
        attributes.extend(
            [
                {"key": "source.file", "value": {"stringValue": source.file}},
                {"key": "source.line", "value": {"intValue": source.line}},
            ],
        )
    return {
        "name": str(record.get("event_name", "runtime.event")),
        "startTimeUnixNano": 0,
        "endTimeUnixNano": 0,
        "attributes": attributes,
    }


def _otel_value(value: object) -> dict[str, object]:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": value}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, (dict, list)):
        return {"stringValue": json.dumps(value, sort_keys=True)}
    return {"stringValue": str(value)}
