"""Tests for DocSync Markdown object parsing."""

from pathlib import Path
from textwrap import dedent

from docsync.markdown.parser import parse_markdown_file

MARKER = "docsync:object"
HEADING_SECTION_END_LINE = 3
EXPLICIT_HEADING_END_LINE = 5
LEGACY_HEADING_END_LINE = 4
FENCED_COMMENT_HEADING_END_LINE = 7


def test_parse_markdown_missing_file_returns_empty_result(tmp_path: Path) -> None:
    """Missing Markdown files produce an empty parse result."""
    result = parse_markdown_file(tmp_path, Path("missing.md"), object_marker=MARKER)

    assert result.objects == {}
    assert result.findings == ()


def test_parse_markdown_resolves_heading_fence_and_plain_blocks(
    tmp_path: Path,
) -> None:
    """Supported Markdown blocks become typed DocSync objects."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object object.heading -->
        # Heading
        Heading body.
        # Next

        <!-- docsync:object object.fence -->
        ```python
        print("demo")
        ```

        <!-- docsync:object object.tilde -->
        ~~~text
        demo
        ~~~

        <!-- docsync:object object.quote -->
        > quoted
        > continued

        <!-- docsync:object object.list -->
        - one
        - two

        <!-- docsync:object object.table -->
        | A |
        | - |

        <!-- docsync:object object.paragraph -->
        Paragraph text.
        Still paragraph text.
        """,
    )

    result = parse_markdown_file(tmp_path, Path("README.md"), object_marker=MARKER)

    assert result.findings == ()
    assert result.objects["object.heading"].kind == "heading_section"
    assert result.objects["object.heading"].title == "Heading"
    assert result.objects["object.heading"].heading_level == 1
    assert result.objects["object.heading"].span.end_line == HEADING_SECTION_END_LINE
    assert result.objects["object.fence"].kind == "code_fence"
    assert result.objects["object.fence"].language == "python"
    assert result.objects["object.tilde"].language == "text"
    assert result.objects["object.quote"].kind == "blockquote"
    assert result.objects["object.list"].kind == "list"
    assert result.objects["object.table"].kind == "table"
    assert result.objects["object.paragraph"].kind == "paragraph"


def test_parse_markdown_reports_duplicate_and_unsupported_markers(
    tmp_path: Path,
) -> None:
    """Duplicate markers and unsupported trailing markers produce findings."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object duplicate -->
        # First

        <!-- docsync:object duplicate -->
        # Second

        <!-- docsync:object open-fence -->
        ```python
        print("unfinished")
        """,
    )

    result = parse_markdown_file(tmp_path, Path("README.md"), object_marker=MARKER)

    assert sorted(result.objects) == ["duplicate"]
    assert [finding.code for finding in result.findings] == ["DS104", "DS103"]


def test_parse_markdown_uses_explicit_object_end_marker(tmp_path: Path) -> None:
    """Explicit object end markers define object span."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object object.heading -->
        # Heading

        Body.
        <!-- docsync:object.end object.heading -->

        Outside object.
        """,
    )

    result = parse_markdown_file(
        tmp_path,
        Path("README.md"),
        object_marker=MARKER,
        require_object_end_markers=True,
    )

    assert result.findings == ()
    assert result.objects["object.heading"].span.end_line == EXPLICIT_HEADING_END_LINE


def test_parse_markdown_preserves_legacy_implicit_object_end(
    tmp_path: Path,
) -> None:
    """Legacy object markers remain valid when strict end markers are disabled."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object object.heading -->
        # Heading

        Body.
        """,
    )

    result = parse_markdown_file(tmp_path, Path("README.md"), object_marker=MARKER)

    assert result.findings == ()
    assert result.objects["object.heading"].span.end_line == LEGACY_HEADING_END_LINE


def test_parse_markdown_ignores_markers_inside_fenced_examples(
    tmp_path: Path,
) -> None:
    """Object marker examples inside fences are not live DocSync markers."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object object.heading -->
        # Heading

        ```markdown
        <!-- docsync:object object.example -->
        # Example
        <!-- docsync:object.end object.example -->
        ```
        <!-- docsync:object.end object.heading -->
        """,
    )

    result = parse_markdown_file(
        tmp_path,
        Path("README.md"),
        object_marker=MARKER,
        require_object_end_markers=True,
    )

    assert result.findings == ()
    assert tuple(result.objects) == ("object.heading",)


def test_parse_markdown_ignores_headings_inside_fenced_examples(
    tmp_path: Path,
) -> None:
    """Heading-section spans ignore heading-looking comments inside fences."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object object.heading -->
        # Heading

        ```toml
        # Not a Markdown heading.
        value = true
        ```
        """,
    )

    result = parse_markdown_file(tmp_path, Path("README.md"), object_marker=MARKER)

    assert result.findings == ()
    assert result.objects["object.heading"].span.end_line == FENCED_COMMENT_HEADING_END_LINE


def test_parse_markdown_reports_missing_object_end_marker_when_required(
    tmp_path: Path,
) -> None:
    """Strict object parsing reports missing explicit end markers."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object object.heading -->
        # Heading
        """,
    )

    result = parse_markdown_file(
        tmp_path,
        Path("README.md"),
        object_marker=MARKER,
        require_object_end_markers=True,
    )

    assert [finding.code for finding in result.findings] == ["DS110"]
    assert "object.heading has no explicit end marker" in result.findings[0].message


def test_parse_markdown_reports_malformed_object_end_markers(
    tmp_path: Path,
) -> None:
    """Mismatched, unexpected, and overlapping end markers are diagnosed."""
    _write_markdown(
        tmp_path,
        """
        <!-- docsync:object.end object.unopened -->

        <!-- docsync:object object.mismatch -->
        # Mismatch
        <!-- docsync:object.end object.other -->

        <!-- docsync:object object.outer -->
        # Outer
        <!-- docsync:object object.inner -->
        ## Inner
        <!-- docsync:object.end object.outer -->
        """,
    )

    result = parse_markdown_file(
        tmp_path,
        Path("README.md"),
        object_marker=MARKER,
        require_object_end_markers=True,
    )

    findings = {(finding.code, finding.message) for finding in result.findings}
    assert findings == {
        (
            "DS111",
            "Object end marker object.other does not match open object object.mismatch.",
        ),
        (
            "DS113",
            "Object marker object.inner starts before object.outer closes.",
        ),
        (
            "DS111",
            "Object end marker object.outer does not match open object object.inner.",
        ),
        (
            "DS112",
            "Object end marker object.unopened has no opening marker.",
        ),
    }


def _write_markdown(tmp_path: Path, text: str) -> None:
    (tmp_path / "README.md").write_text(
        dedent(text).lstrip(),
        encoding="utf-8",
    )
