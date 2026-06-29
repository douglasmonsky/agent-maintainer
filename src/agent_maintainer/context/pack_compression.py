"""Compression helpers for context pack supporting evidence."""

from __future__ import annotations

from dataclasses import dataclass

from agent_maintainer.context.compression import CompressionRequest, CompressionResult
from agent_maintainer.context.compression_backends import (
    compress,
    extractive_compress,
)
from agent_maintainer.context.headroom_backend import (
    BACKEND_HEADROOM,
    CompressionBackendError,
    CompressionBackendUnavailable,
)

HEADROOM_FALLBACK_WARNING = "Headroom compression failed; using deterministic extractive context."


@dataclass(frozen=True)
class PackCompressionRequest:
    """Compression settings for context pack supporting content."""

    backend: str = ""
    target_chars: int = 0
    required: bool = False


@dataclass(frozen=True)
class PackCompressionResult:
    """Compressed context-pack supporting content."""

    logs: list[dict[str, object]]
    files: list[dict[str, object]]
    payload: dict[str, object]
    warnings: tuple[str, ...] = ()


def compress_supporting_context(
    *,
    logs: list[dict[str, object]],
    files: list[dict[str, object]],
    request: PackCompressionRequest,
) -> PackCompressionResult:
    """Compress context pack supporting logs and file outlines."""

    if not request.backend:
        return PackCompressionResult(logs=logs, files=files, payload={"enabled": False})
    warnings: list[str] = []
    compressed_logs = compress_items(logs, kind="log", request=request, warnings=warnings)
    compressed_files = compress_items(files, kind="file", request=request, warnings=warnings)
    return PackCompressionResult(
        logs=compressed_logs,
        files=compressed_files,
        payload=compression_payload(request, warnings),
        warnings=tuple(unique_warnings(warnings)),
    )


def compress_items(
    items: list[dict[str, object]],
    *,
    kind: str,
    request: PackCompressionRequest,
    warnings: list[str],
) -> list[dict[str, object]]:
    """Return compressed copies of context-pack supporting items."""

    return [compress_item(item, kind=kind, request=request, warnings=warnings) for item in items]


def compress_item(
    item: dict[str, object],
    *,
    kind: str,
    request: PackCompressionRequest,
    warnings: list[str],
) -> dict[str, object]:
    """Return compressed copy of one supporting-context item."""

    text = item.get("text", "")
    if not isinstance(text, str) or not text:
        return item
    compression_request = CompressionRequest(
        content=text,
        content_kind=kind,
        target_chars=target_chars(request, text),
        preserve_terms=(),
    )
    result = compress_or_fallback(compression_request, request=request, warnings=warnings)
    updated = dict(item)
    updated["text"] = result.content
    updated["compression"] = result_metadata(result)
    return updated


def compress_or_fallback(
    compression_request: CompressionRequest,
    *,
    request: PackCompressionRequest,
    warnings: list[str],
) -> CompressionResult:
    """Compress one item or use deterministic fallback when allowed."""

    try:
        return compress(compression_request, backend=request.backend)
    except CompressionBackendUnavailable as exc:
        return fallback_or_raise(
            compression_request,
            request=request,
            warnings=warnings,
            message=str(exc),
            exception=exc,
        )
    except CompressionBackendError as exc:
        return fallback_or_raise(
            compression_request,
            request=request,
            warnings=warnings,
            message=headroom_fallback_message(request.backend),
            exception=exc,
        )


def fallback_or_raise(
    compression_request: CompressionRequest,
    *,
    request: PackCompressionRequest,
    warnings: list[str],
    message: str,
    exception: Exception,
) -> CompressionResult:
    """Return extractive fallback unless compression was required."""

    if request.required:
        raise exception
    warnings.append(message)
    return extractive_compress(compression_request)


def headroom_fallback_message(backend: str) -> str:
    """Return fallback warning for optional provider failure."""

    if backend == BACKEND_HEADROOM:
        return HEADROOM_FALLBACK_WARNING
    return f"{backend} compression failed; using deterministic extractive context."


def target_chars(request: PackCompressionRequest, text: str) -> int:
    """Return target character budget for one supporting item."""

    if request.target_chars > 0:
        return request.target_chars
    return len(text)


def result_metadata(result: CompressionResult) -> dict[str, object]:
    """Return serializable compression metadata for one item."""

    return {
        "backend": result.backend,
        "original_chars": result.original_chars,
        "compressed_chars": result.compressed_chars,
        "exact_facts_preserved": result.exact_facts_preserved,
        "warnings": list(result.warnings),
    }


def compression_payload(request: PackCompressionRequest, warnings: list[str]) -> dict[str, object]:
    """Return serializable context-pack compression summary."""

    return {
        "enabled": True,
        "backend": request.backend,
        "required": request.required,
        "target_chars": request.target_chars,
        "warnings": list(unique_warnings(warnings)),
    }


def unique_warnings(warnings: list[str]) -> tuple[str, ...]:
    """Return warnings in stable first-seen order."""

    return tuple(dict.fromkeys(warnings))
