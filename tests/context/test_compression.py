"""Tests deterministic context compression backends."""

from __future__ import annotations

import sys

import pytest

from agent_maintainer.context.compression import CompressionRequest
from agent_maintainer.context.compression_backends import (
    BACKEND_EXTRACTIVE,
    BACKEND_NONE,
    BACKEND_TRUNCATE,
    compress,
    extractive_compress,
    none_compress,
    truncate_compress,
)


def test_none_backend_returns_original_content() -> None:
    """None backend returns input unchanged."""

    request = request_for("alpha\nkeep-token\nomega", target_chars=5)

    result = none_compress(request)

    assert result.backend == BACKEND_NONE
    assert result.content == request.content
    assert result.original_chars == len(request.content)
    assert result.compressed_chars == len(request.content)
    assert result.exact_facts_preserved


def test_truncate_backend_bounds_prefix_content() -> None:
    """Truncate backend returns deterministic prefix."""

    request = request_for("alpha beta gamma", target_chars=5, preserve_terms=("gamma",))

    result = truncate_compress(request)

    assert result.backend == BACKEND_TRUNCATE
    assert result.content == "alpha"
    assert not result.exact_facts_preserved


def test_extractive_backend_preserves_required_lines() -> None:
    """Extractive backend keeps lines containing preserve terms."""

    request = request_for(
        "intro\nimportant exact-token detail\nother context",
        target_chars=18,
        preserve_terms=("exact-token",),
    )

    result = extractive_compress(request)

    assert result.backend == BACKEND_EXTRACTIVE
    assert "exact-token" in result.content
    assert result.exact_facts_preserved
    assert "target_chars exceeded" in result.warnings[0]


def test_named_compression_falls_back_when_preserve_terms_drop() -> None:
    """Named compression falls back to extractive when facts disappear."""

    request = request_for(
        "intro\nimportant exact-token detail\nother context",
        target_chars=8,
        preserve_terms=("exact-token",),
    )

    result = compress(request, backend=BACKEND_TRUNCATE)

    assert result.backend == BACKEND_EXTRACTIVE
    assert "exact-token" in result.content
    assert result.exact_facts_preserved
    assert any("used extractive fallback" in warning for warning in result.warnings)


def test_named_compression_rejects_unknown_backend() -> None:
    """Unknown compression backends fail clearly."""

    with pytest.raises(ValueError, match="unknown compression backend"):
        compress(request_for("content"), backend="headroom")


def test_request_rejects_invalid_values() -> None:
    """Request validation rejects invalid budgets and empty terms."""

    with pytest.raises(ValueError, match="target_chars"):
        request_for("content", target_chars=-1)
    with pytest.raises(ValueError, match="content_kind"):
        CompressionRequest(
            content="content",
            content_kind="",
            target_chars=10,
            preserve_terms=(),
        )
    with pytest.raises(ValueError, match="preserve_terms"):
        request_for("content", preserve_terms=("",))


def test_phase25_backends_do_not_import_headroom() -> None:
    """Deterministic compression phase does not depend on Headroom."""

    compress(request_for("content"), backend=BACKEND_NONE)

    assert "headroom" not in sys.modules


def request_for(
    content: str,
    *,
    target_chars: int = 20,
    preserve_terms: tuple[str, ...] = ("keep-token",),
) -> CompressionRequest:
    """Return compression request fixture."""

    return CompressionRequest(
        content=content,
        content_kind="markdown",
        target_chars=target_chars,
        preserve_terms=preserve_terms,
    )
