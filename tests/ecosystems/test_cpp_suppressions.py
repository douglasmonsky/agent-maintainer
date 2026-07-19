"""Tests C/C++ suppression classification."""

from __future__ import annotations

import pytest

from agent_maintainer.ecosystems.cpp import suppressions


def test_cpp_nolint_broadness() -> None:
    """NOLINT markers are narrow only when they name a rule."""
    broad = suppressions.classify_line("value(); // NOLINT")
    narrow = suppressions.classify_line("value(); // NOLINT(readability-identifier-naming)")
    next_line = suppressions.classify_line("// NOLINTNEXTLINE(bugprone-use-after-move)")

    assert [(item.kind, item.broad) for item in broad] == [("nolint", True)]
    assert [(item.kind, item.broad) for item in narrow] == [("nolint", False)]
    assert [(item.kind, item.broad) for item in next_line] == [("nolint-next-line", False)]


def test_cpp_nolint_region_and_cppcheck_forms() -> None:
    """Region and cppcheck markers expose their exact broadness."""
    assert suppressions.classify_line("// NOLINTBEGIN")[0].broad is True
    assert suppressions.classify_line("// NOLINTEND")[0].kind == "nolint-end"
    assert suppressions.classify_line("// cppcheck-suppress nullPointer")[0].broad is False
    assert suppressions.classify_line("// cppcheck-suppress-file")[0].broad is True


def test_cppcheck_suppression_file_requires_recognized_path() -> None:
    """Only exact cppcheck suppression filenames classify plain entries."""
    finding = suppressions.classify_line("uninitvar", path="cppcheck-suppressions.txt")

    assert [(item.kind, item.broad) for item in finding] == [("cppcheck-suppression-file", False)]
    assert suppressions.classify_line("uninitvar", path="notes.txt") == ()


def test_cpp_marker_families_follow_source_order() -> None:
    """Each marker family contributes once in deterministic source order."""
    findings = suppressions.classify_line(
        "// cppcheck-suppress nullPointer NOLINT NOLINT(readability-magic-numbers)"
    )

    assert [item.kind for item in findings] == ["cppcheck-suppress", "nolint"]


@pytest.mark.parametrize(
    "line",
    (
        "// NOLINTfoo",
        "// NOLINT_value",
        "// NOLINT1",
        "// NOLINT(",
        "// NOLINT(rule",
        "// NOLINT(rule)extra",
        "// NOLINTNEXTLINEfoo",
        "// NOLINTBEGIN_extra",
        "// NOLINTEND2",
    ),
)
def test_cpp_nolint_requires_an_exact_complete_marker(line: str) -> None:
    """NOLINT-like identifiers and incomplete rule lists are ignored."""
    assert suppressions.classify_line(line) == ()


@pytest.mark.parametrize(
    "line",
    (
        "// cppcheck-suppressions",
        "// cppcheck-suppress_file",
        "// cppcheck-suppressX",
        "// cppcheck-suppress-file-extra",
        "// cppcheck-suppress-file_extra",
        "// cppcheck-suppress-fileX",
        "/* cppcheck-suppress nullPointer*extra */",
    ),
)
def test_cppcheck_requires_an_exact_marker_name(line: str) -> None:
    """Longer cppcheck-like identifiers are not suppression markers."""
    assert suppressions.classify_line(line) == ()


def test_cpp_exact_markers_allow_complete_lists_and_trailing_whitespace() -> None:
    """Complete rule lists and whitespace-delimited markers remain valid."""
    empty = suppressions.classify_line("// NOLINT() explanation")
    named = suppressions.classify_line("// NOLINT(readability-magic-numbers) explanation")
    cppcheck = suppressions.classify_line("/* cppcheck-suppress */")
    cppcheck_file = suppressions.classify_line("/* cppcheck-suppress-file */")

    assert [(item.kind, item.broad) for item in empty] == [("nolint", True)]
    assert [(item.kind, item.broad) for item in named] == [("nolint", False)]
    assert [(item.kind, item.broad) for item in cppcheck] == [("cppcheck-suppress", True)]
    assert [(item.kind, item.broad) for item in cppcheck_file] == [("cppcheck-suppress-file", True)]


def test_cpp_nolint_allows_non_identifier_terminators() -> None:
    """NOLINT markers may end before punctuation or a block-comment close."""
    block = suppressions.classify_line("/* NOLINT*/")
    explained = suppressions.classify_line("// NOLINT: explanation")
    named = suppressions.classify_line("// NOLINT(readability-magic-numbers): explanation")

    assert [(item.kind, item.broad) for item in block] == [("nolint", True)]
    assert [(item.kind, item.broad) for item in explained] == [("nolint", True)]
    assert [(item.kind, item.broad) for item in named] == [("nolint", False)]


def test_cppcheck_markers_allow_adjacent_block_comment_close() -> None:
    """Cppcheck directives remain exact when immediately followed by */."""
    broad = suppressions.classify_line("/* cppcheck-suppress*/")
    broad_file = suppressions.classify_line("/* cppcheck-suppress-file*/")
    narrow = suppressions.classify_line("/* cppcheck-suppress nullPointer*/")

    assert [(item.kind, item.broad) for item in broad] == [("cppcheck-suppress", True)]
    assert [(item.kind, item.broad) for item in broad_file] == [("cppcheck-suppress-file", True)]
    assert [(item.kind, item.broad) for item in narrow] == [("cppcheck-suppress", False)]
