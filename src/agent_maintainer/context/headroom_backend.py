"""Optional Headroom compression adapter."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from agent_maintainer.context.compression import CompressionRequest

BACKEND_HEADROOM = "headroom"
HEADROOM_INSTALL_MESSAGE = (
    "Headroom compression requested but not installed. Install: python -m pip "
    'install "agent-maintainer[compression]"'
)


class CompressionBackendUnavailable(RuntimeError):
    """Raised when an optional compression backend is not installed."""


class CompressionBackendError(RuntimeError):
    """Raised when an optional compression backend fails."""


def headroom_content(request: CompressionRequest) -> str:
    """Return Headroom-compressed text through optional dependency."""

    compressor = load_headroom_compressor()
    return run_headroom_compressor(compressor, request)


def load_headroom_compressor() -> Callable[..., Any]:
    """Return Headroom compression callable from optional dependency."""

    try:
        module = importlib.import_module("headroom")
    except ImportError as exc:
        raise CompressionBackendUnavailable(HEADROOM_INSTALL_MESSAGE) from exc
    compressor = getattr(module, "compress", None)
    if not callable(compressor):
        raise CompressionBackendUnavailable("Headroom package does not expose compress")
    return compressor


def run_headroom_compressor(compressor: Callable[..., Any], request: CompressionRequest) -> str:
    """Run Headroom compressor and normalize common result shapes."""

    try:
        result = compressor(request.content)
    except Exception as exc:
        raise CompressionBackendError("Headroom compression failed") from exc
    return normalized_headroom_content(result)


def normalized_headroom_content(result: object) -> str:
    """Return compressed text from common Headroom result shapes."""

    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return dict_result_content(result)
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    raise CompressionBackendError("Headroom compression returned unsupported result")


def dict_result_content(result: dict[object, object]) -> str:
    """Return compressed text from dictionary result."""

    for key in ("content", "text", "compressed"):
        value = result.get(key)
        if isinstance(value, str):
            return value
    raise CompressionBackendError("Headroom compression returned unsupported result")
