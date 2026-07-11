"""Optional Headroom compression adapter."""

from __future__ import annotations

import importlib
from collections.abc import Callable

from agent_context.compression.models import CompressionRequest
from agent_context.structured_values import json_array, json_object

BACKEND_HEADROOM = "headroom"
# docsync:evidence.start evidence.context_compression.headroom_boundary
HEADROOM_INSTALL_MESSAGE = (
    "Headroom compression requested but not installed. Install: python -m pip "
    'install "agent-maintainer[compression]"'
)
MESSAGE_ROLE = "user"


class CompressionBackendUnavailable(RuntimeError):
    """Raised when an optional compression backend is not installed."""


class CompressionBackendError(RuntimeError):
    """Raised when a compression backend fails."""


def headroom_content(request: CompressionRequest) -> str:
    """Return Headroom-compressed text through the optional dependency."""
    compressor = load_headroom_compressor()
    return run_headroom_compressor(compressor, request)


def load_headroom_compressor() -> Callable[..., object]:
    """Return the Headroom compression callable from the optional dependency."""
    try:
        module = importlib.import_module("headroom")
    except ImportError as exc:
        raise CompressionBackendUnavailable(HEADROOM_INSTALL_MESSAGE) from exc
    compressor = getattr(module, "compress", None)
    if not callable(compressor):
        raise CompressionBackendUnavailable("Headroom package does not expose compress")
    return compressor


def run_headroom_compressor(
    compressor: Callable[..., object],
    request: CompressionRequest,
) -> str:
    """Run Headroom compressor and normalize common result shapes."""
    try:
        result = compressor(headroom_messages(request))
    except Exception as exc:
        raise CompressionBackendError("Headroom compression failed") from exc
    return normalized_headroom_content(result)


def headroom_messages(request: CompressionRequest) -> list[dict[str, str]]:
    """Return Headroom-compatible messages for sanitized supporting context."""
    return [
        {
            "role": MESSAGE_ROLE,
            "content": request.content,
        },
    ]


# docsync:evidence.end evidence.context_compression.headroom_boundary


def normalized_headroom_content(result: object) -> str:
    """Return compressed text from common Headroom result shapes."""
    if isinstance(result, str):
        return result
    result_object = json_object(result)
    if result_object is not None:
        return dict_result_content(result_object)
    messages_text = messages_content(getattr(result, "messages", None))
    if messages_text:
        return messages_text
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    raise CompressionBackendError("Headroom compression returned unsupported result")


def dict_result_content(result: dict[str, object]) -> str:
    """Return compressed text from a dictionary result."""
    messages_text = messages_content(result.get("messages"))
    if messages_text:
        return messages_text
    for key in ("content", "text", "compressed"):
        value = result.get(key)
        if isinstance(value, str):
            return value
    raise CompressionBackendError("Headroom compression returned unsupported result")


def messages_content(messages: object) -> str:
    """Return joined content from Headroom-style messages."""
    values = json_array(messages)
    if values is None:
        return ""
    parts: list[str] = []
    for message in values:
        content = message_content(message)
        if content:
            parts.append(content)
    return "\n".join(parts)


def message_content(message: object) -> str:
    """Return content from one Headroom-style message."""
    payload = json_object(message)
    content = getattr(message, "content", None) if payload is None else payload.get("content")
    if isinstance(content, str):
        return content
    return ""
