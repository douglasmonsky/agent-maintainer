"""Tests C/C++ suppression classification."""

from __future__ import annotations

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
