"""Deterministic context compression backends."""

from __future__ import annotations

from collections.abc import Callable

from agent_context.compression.headroom import BACKEND_HEADROOM, headroom_content
from agent_context.compression.models import CompressionRequest, CompressionResult

BACKEND_NONE = "none"
BACKEND_TRUNCATE = "truncate"
BACKEND_EXTRACTIVE = "extractive"
FALLBACK_WARNING = "backend dropped preserve terms; used extractive fallback"

Backend = Callable[[CompressionRequest], CompressionResult]


# docsync:evidence.start evidence.context_compression.deterministic_backends
def compress(request: CompressionRequest, *, backend: str) -> CompressionResult:
    """Compress context with a named backend."""

    selected = backend_function(backend)
    result = selected(request)
    if result.exact_facts_preserved or backend == BACKEND_EXTRACTIVE:
        return result
    fallback = extractive_compress(request)
    return append_warning(fallback, f"{backend} {FALLBACK_WARNING}")


def backend_function(backend: str) -> Backend:
    """Return backend implementation or reject unknown names."""

    backends: dict[str, Backend] = {
        BACKEND_HEADROOM: headroom_compress,
        BACKEND_NONE: none_compress,
        BACKEND_TRUNCATE: truncate_compress,
        BACKEND_EXTRACTIVE: extractive_compress,
    }
    try:
        return backends[backend]
    except KeyError as exc:
        names = ", ".join(sorted(backends))
        message = f"unknown compression backend {backend!r}; expected one of {names}"
        raise ValueError(message) from exc


def none_compress(request: CompressionRequest) -> CompressionResult:
    """Return original content unchanged."""

    return result_for(
        request,
        content=request.content,
        backend=BACKEND_NONE,
        warnings=forbidden_warnings(request, request.content),
    )


def truncate_compress(request: CompressionRequest) -> CompressionResult:
    """Return deterministic prefix-bounded content."""

    content = request.content
    if len(request.content) > request.target_chars:
        content = request.content[: request.target_chars]
    return result_for(
        request,
        content=content,
        backend=BACKEND_TRUNCATE,
        warnings=forbidden_warnings(request, content),
    )


def extractive_compress(request: CompressionRequest) -> CompressionResult:
    """Return line-based extractive content preserving required terms."""

    preserved = preserve_lines(request)
    remaining = budget_remaining(request.target_chars, preserved)
    filler = filler_lines(request, preserved, remaining)
    content = "\n".join((*preserved, *filler)).strip()
    warnings = tuple(target_warnings(request, content))
    warnings += forbidden_warnings(request, content)
    return result_for(
        request,
        content=content,
        backend=BACKEND_EXTRACTIVE,
        warnings=warnings,
    )


def headroom_compress(request: CompressionRequest) -> CompressionResult:
    """Return Headroom-compressed content through optional dependency."""

    compressed = headroom_content(request)
    return result_for(
        request,
        content=compressed,
        backend=BACKEND_HEADROOM,
        warnings=forbidden_warnings(request, compressed),
    )


def preserve_lines(request: CompressionRequest) -> tuple[str, ...]:
    """Return source lines containing preserve terms."""

    lines = split_lines(request.content)
    return tuple(line for line in lines if any(term in line for term in request.preserve_terms))


def filler_lines(
    request: CompressionRequest, preserved: tuple[str, ...], remaining_chars: int
) -> tuple[str, ...]:
    """Return non-preserved lines that fit the remaining target."""

    if remaining_chars <= 0:
        return ()
    result: list[str] = []
    used = 0
    preserved_set = set(preserved)
    for line in split_lines(request.content):
        if line in preserved_set or has_forbidden_term(request, line):
            continue
        next_size = used + len(line) + separator_chars(result)
        if next_size > remaining_chars:
            break
        result.append(line)
        used = next_size
    return tuple(result)


def split_lines(content: str) -> tuple[str, ...]:
    """Return non-empty content lines."""

    return tuple(line for line in content.splitlines() if line.strip())


def budget_remaining(target_chars: int, preserved: tuple[str, ...]) -> int:
    """Return approximate remaining budget after preserved lines."""

    preserved_chars = len("\n".join(preserved))
    return target_chars - preserved_chars


def separator_chars(existing_lines: list[str]) -> int:
    """Return newline cost before appending another line."""

    return 1 if existing_lines else 0


def target_warnings(request: CompressionRequest, content: str) -> tuple[str, ...]:
    """Return target-budget warnings."""

    if len(content) <= request.target_chars:
        return ()
    return ("target_chars exceeded to preserve required terms",)


def forbidden_warnings(request: CompressionRequest, content: str) -> tuple[str, ...]:
    """Return warnings when forbidden terms survive compression."""

    if not has_forbidden_term(request, content):
        return ()
    return ("compressed content contains forbidden terms",)


def has_forbidden_term(request: CompressionRequest, content: str) -> bool:
    """Return whether content contains a forbidden term."""

    return any(term in content for term in request.forbidden_terms)


def result_for(
    request: CompressionRequest,
    *,
    content: str,
    backend: str,
    warnings: tuple[str, ...] = (),
) -> CompressionResult:
    """Build compression result for selected content."""

    return CompressionResult(
        content=content,
        backend=backend,
        original_chars=len(request.content),
        compressed_chars=len(content),
        exact_facts_preserved=preserve_terms_present(request, content),
        warnings=warnings,
    )


def preserve_terms_present(request: CompressionRequest, content: str) -> bool:
    """Return whether all preserve terms remain in content."""

    return all(term in content for term in request.preserve_terms)


def append_warning(result: CompressionResult, warning: str) -> CompressionResult:
    """Return result with extra warning appended."""

    return CompressionResult(
        content=result.content,
        backend=result.backend,
        original_chars=result.original_chars,
        compressed_chars=result.compressed_chars,
        exact_facts_preserved=result.exact_facts_preserved,
        warnings=(*result.warnings, warning),
    )


# docsync:evidence.end evidence.context_compression.deterministic_backends
