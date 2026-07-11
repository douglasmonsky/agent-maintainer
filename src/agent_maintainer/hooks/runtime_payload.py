"""Structured stdin and stdout boundaries for hook runtime."""

from __future__ import annotations

import json
from typing import TextIO

from agent_maintainer.core.structured_values import json_object


def read_hook_payload(stream: TextIO) -> dict[str, object]:
    """Read one hook payload, treating malformed input as empty."""

    try:
        payload: object = json.load(stream)
    except (json.JSONDecodeError, OSError):
        return {}
    return json_object(payload) or {}


def render_hook_payload(payload: dict[str, object]) -> str:
    """Render one compact JSON hook response."""

    return json.dumps(payload)
