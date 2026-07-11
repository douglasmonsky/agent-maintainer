"""Tests deterministic context compression backends."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from agent_context.compression import headroom as headroom_backend
from agent_context.compression.backends import (
    BACKEND_EXTRACTIVE,
    BACKEND_NONE,
    BACKEND_TRUNCATE,
    compress,
    extractive_compress,
    none_compress,
    truncate_compress,
)
from agent_context.compression.headroom import (
    BACKEND_HEADROOM,
    CompressionBackendError,
    CompressionBackendUnavailable,
)
from agent_context.compression.models import CompressionRequest
from agent_maintainer.context.compression import backends as compatibility_backends
from agent_maintainer.context.compression import headroom as compatibility_headroom
from agent_maintainer.context.compression.models import (
    CompressionRequest as CompatibilityCompressionRequest,
)
from tests.support.callbacks import constant_callback


def test_context_compression_compatibility_shims() -> None:
    """Old product paths forward to reusable compression helpers."""

    assert compatibility_backends.compress is compress
    assert compatibility_headroom.BACKEND_HEADROOM == BACKEND_HEADROOM
    assert CompatibilityCompressionRequest is CompressionRequest


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
        compress(request_for("content"), backend="missing")


def test_headroom_backend_uses_optional_compress_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Headroom backend uses optional package when available."""
    received: list[list[dict[str, str]]] = []

    def compress_messages(messages: list[dict[str, str]]) -> object:
        received.append(messages)
        return SimpleNamespace(messages=[{"content": "compressed: content"}])

    fake_module = SimpleNamespace(compress=compress_messages)
    monkeypatch.setattr(
        headroom_backend.importlib,
        "import_module",
        constant_callback(fake_module),
    )

    result = compress(request_for("content", preserve_terms=()), backend=BACKEND_HEADROOM)

    assert result.backend == BACKEND_HEADROOM
    assert result.content == "compressed: content"
    assert received == [[{"role": "user", "content": "content"}]]


def test_headroom_backend_reports_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Headroom backend reports install guidance when missing."""

    def missing_module(_name: str) -> object:
        raise ImportError("missing")

    monkeypatch.setattr(headroom_backend.importlib, "import_module", missing_module)

    with pytest.raises(CompressionBackendUnavailable, match="agent-maintainer"):
        compress(request_for("content"), backend=BACKEND_HEADROOM)


def test_headroom_backend_reports_missing_compress_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Headroom backend reports package shape mismatch."""

    fake_module = SimpleNamespace()
    monkeypatch.setattr(
        headroom_backend.importlib,
        "import_module",
        constant_callback(fake_module),
    )

    with pytest.raises(CompressionBackendUnavailable, match="does not expose compress"):
        compress(request_for("content"), backend=BACKEND_HEADROOM)


def test_headroom_backend_reports_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Headroom provider failures are normalized."""

    def fail_compress(_messages: list[dict[str, str]]) -> str:
        raise RuntimeError("provider failed")

    fake_module = SimpleNamespace(compress=fail_compress)
    monkeypatch.setattr(
        headroom_backend.importlib,
        "import_module",
        constant_callback(fake_module),
    )

    with pytest.raises(CompressionBackendError, match="Headroom compression failed"):
        compress(request_for("content"), backend=BACKEND_HEADROOM)


def test_headroom_backend_normalizes_common_result_shapes() -> None:
    """Headroom adapter accepts common provider response shapes."""

    assert headroom_backend.normalized_headroom_content({"compressed": "dict text"})
    assert (
        headroom_backend.normalized_headroom_content(
            {"messages": [None, {"content": "dict message"}]},
        )
        == "dict message"
    )
    assert (
        headroom_backend.normalized_headroom_content(
            SimpleNamespace(
                messages=[
                    {"content": "first"},
                    SimpleNamespace(content="second"),
                ],
            ),
        )
        == "first\nsecond"
    )
    assert (
        headroom_backend.normalized_headroom_content(
            SimpleNamespace(content="content attr"),
        )
        == "content attr"
    )
    assert (
        headroom_backend.normalized_headroom_content(SimpleNamespace(text="text attr"))
        == "text attr"
    )


def test_request_rejects_invalid_values() -> None:
    """Request validation rejects invalid budgets and empty terms."""

    assert request_for("content").metadata == {}
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
