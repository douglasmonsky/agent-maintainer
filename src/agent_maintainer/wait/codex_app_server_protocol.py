"""JSON-RPC protocol values for the Codex app-server wait client."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

APP_SERVER_COMPLETED_METHODS: Final = frozenset(
    ("turn/completed", "turn.completed"),
)
APP_SERVER_THREAD_READ_PROBE_REQUEST_ID: Final = 2
APP_SERVER_TURN_START_REQUEST_ID: Final = 3
APP_SERVER_THREAD_READ_REQUEST_START_ID: Final = 1000
APP_SERVER_TERMINAL_TURN_STATUSES: Final = frozenset(
    ("completed", "failed", "interrupted"),
)
JsonMessage = dict[str, object]


@dataclass(frozen=True)
class JsonRpcResponse:
    """Observed app-server JSON-RPC response."""

    request_id: int
    result: Mapping[str, object] | None = None
    error: str = ""


def app_server_messages(thread_id: str, prompt: str) -> tuple[JsonMessage, ...]:
    """Return initialize, resume, and turn-start messages."""

    return (
        *_app_server_initialize_messages(),
        {"id": 2, "method": "thread/resume", "params": {"threadId": thread_id}},
        {
            "id": APP_SERVER_TURN_START_REQUEST_ID,
            "method": "turn/start",
            "params": {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt}],
            },
        },
    )


def app_server_probe_messages(thread_id: str) -> tuple[JsonMessage, ...]:
    """Return initialize and read-only thread-probe messages."""

    return (
        *_app_server_initialize_messages(),
        {
            "id": APP_SERVER_THREAD_READ_PROBE_REQUEST_ID,
            "method": "thread/read",
            "params": {"threadId": thread_id, "includeTurns": False},
        },
    )


def parse_app_server_line(line: str) -> JsonRpcResponse | None:
    """Parse one JSON-RPC response line, ignoring notifications."""

    payload = _json_object(line)
    request_id = payload.get("id")
    if not isinstance(request_id, int):
        return None
    error = payload.get("error")
    if isinstance(error, Mapping):
        message = str(error.get("message") or "Codex app-server error")
        return JsonRpcResponse(request_id, error=message)
    result = payload.get("result")
    mapped_result = result if isinstance(result, Mapping) else None
    return JsonRpcResponse(request_id, result=mapped_result)


def app_server_turn_completed(line: str) -> bool:
    """Return whether a notification reports terminal turn completion."""

    payload = _json_object(line)
    observed = (payload.get("method"), payload.get("type"))
    return any(value in APP_SERVER_COMPLETED_METHODS for value in observed)


def _app_server_initialize_messages() -> tuple[JsonMessage, ...]:
    return (
        {
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "agent_maintainer",
                    "title": "Agent Maintainer",
                    "version": "0.0.0",
                },
            },
        },
        {"method": "initialized", "params": {}},
    )


def _json_object(line: str) -> dict[str, object]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
