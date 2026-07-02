"""Tests for DocSync Markdown object parsing."""

from pathlib import Path
from textwrap import dedent

from docsync.markdown.parser import parse_markdown_file

MARKER = "docsync:object"
HEADING_SECTION_END_LINE = 3


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


def _write_markdown(tmp_path: Path, text: str) -> None:
    (tmp_path / "README.md").write_text(
        dedent(text).lstrip(),
        encoding="utf-8",
    )
