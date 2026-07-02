"""Parse Markdown hidden DocSync object markers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docsync.core.fingerprints import sha256_text
from docsync.core.models import DocObject, Finding, LineSpan

HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")


@dataclass(frozen=True)
class MarkdownParseResult:
    """Resolved Markdown objects and parser findings."""

    objects: dict[str, DocObject]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ObjectBlock:
    """Resolved Markdown block details for one DocSync object."""

    object_id: str
    kind: str
    marker_line: int
    end_line: int
    title: str | None
    heading_line: int | None = None
    heading_level: int | None = None
    language: str | None = None


@dataclass(frozen=True)
class ResolveContext:
    """Inputs needed to resolve one Markdown object marker."""

    path: Path
    lines: list[str]
    marker_line: int
    object_id: str
    block_line: int


def parse_markdown_file(
    repo_root: Path,
    path: Path,
    *,
    object_marker: str,
) -> MarkdownParseResult:
    """Parse one Markdown file for hidden DocSync object markers."""

    full_path = repo_root / path
    if not full_path.exists():
        return MarkdownParseResult(objects={}, findings=())
    lines = full_path.read_text(encoding="utf-8").splitlines()
    objects: dict[str, DocObject] = {}
    findings: list[Finding] = []
    for line_number, line in enumerate(lines, start=1):
        object_id = _marker_id(line, object_marker)
        if object_id is None:
            continue
        if object_id in objects:
            findings.append(_finding("DS104", f"Duplicate marker {object_id}.", path, line_number))
            continue
        resolved = _resolve_object(path, lines, line_number, object_id)
        if resolved is None:
            findings.append(
                _finding(
                    "DS103",
                    f"Marker {object_id} not attached to supported Markdown block.",
                    path,
                    line_number,
                )
            )
            continue
        objects[object_id] = resolved
    return MarkdownParseResult(objects=objects, findings=tuple(findings))


def _resolve_object(
    path: Path,
    lines: list[str],
    marker_line: int,
    object_id: str,
) -> DocObject | None:
    """Resolve one marker to the Markdown block that follows it."""

    block_line = _next_nonblank(lines, marker_line + 1)
    if block_line is None:
        return None
    context = ResolveContext(
        path=path,
        lines=lines,
        marker_line=marker_line,
        object_id=object_id,
        block_line=block_line,
    )
    line = lines[block_line - 1]
    heading = HEADING_RE.match(line)
    if heading is not None:
        return _heading_object(context, heading)
    fence = _fence_marker(line)
    if fence is not None:
        return _fence_object(context, fence)
    return _plain_object(context, line)


def _heading_object(context: ResolveContext, heading: re.Match[str]) -> DocObject:
    """Return a heading-section documentation object."""

    level = len(heading.group("marks"))
    block = ObjectBlock(
        object_id=context.object_id,
        kind="heading_section",
        marker_line=context.marker_line,
        end_line=_heading_section_end(context.lines, context.block_line, level),
        title=heading.group("title").strip(),
        heading_line=context.block_line,
        heading_level=level,
    )
    return _doc_object(context.path, context.lines, block)


def _fence_object(context: ResolveContext, fence: str) -> DocObject | None:
    """Return a code-fence documentation object."""

    end_line = _fence_end(context.lines, context.block_line, fence)
    if end_line is None:
        return None
    fence_prefix_length = len(fence)
    language = context.lines[context.block_line - 1].strip()[fence_prefix_length:].strip() or None
    block = ObjectBlock(
        object_id=context.object_id,
        kind="code_fence",
        marker_line=context.marker_line,
        end_line=end_line,
        title=None,
        language=language,
    )
    return _doc_object(context.path, context.lines, block)


def _plain_object(context: ResolveContext, line: str) -> DocObject | None:
    """Return a plain Markdown block documentation object."""

    kind = _plain_block_kind(line)
    if kind is None:
        return None
    block = ObjectBlock(
        object_id=context.object_id,
        kind=kind,
        marker_line=context.marker_line,
        end_line=_plain_block_end(context.lines, context.block_line),
        title=None,
    )
    return _doc_object(context.path, context.lines, block)


def _doc_object(path: Path, lines: list[str], block: ObjectBlock) -> DocObject:
    """Return one documentation object."""

    marker_index = block.marker_line - 1
    block_end_index = block.end_line
    content = "\n".join(lines[marker_index:block_end_index])
    return DocObject(
        object_id=block.object_id,
        path=path,
        kind=block.kind,
        marker_line=block.marker_line,
        span=LineSpan(path=path, start_line=block.marker_line, end_line=block.end_line),
        title=block.title,
        content_hash=sha256_text(content),
        heading_line=block.heading_line,
        heading_level=block.heading_level,
        language=block.language,
    )


def _marker_id(line: str, object_marker: str) -> str | None:
    """Return object ID from a hidden Markdown marker."""

    stripped = line.strip()
    prefix = f"<!-- {object_marker}"
    if not stripped.startswith(prefix) or not stripped.endswith("-->"):
        return None
    prefix_length = len(prefix)
    marker_end = -3
    return stripped[prefix_length:marker_end].strip()


def _next_nonblank(lines: list[str], start_line: int) -> int | None:
    """Return next nonblank line number."""

    for line_number in range(start_line, len(lines) + 1):
        if lines[line_number - 1].strip():
            return line_number
    return None


def _heading_section_end(lines: list[str], heading_line: int, level: int) -> int:
    """Return the inclusive line where a heading section ends."""

    for line_number in range(heading_line + 1, len(lines) + 1):
        heading = HEADING_RE.match(lines[line_number - 1])
        if heading is not None and len(heading.group("marks")) <= level:
            return line_number - 1
    return len(lines)


def _fence_marker(line: str) -> str | None:
    """Return Markdown fence marker from a line."""

    stripped = line.lstrip()
    if stripped.startswith("```"):
        return "```"
    if stripped.startswith("~~~"):
        return "~~~"
    return None


def _fence_end(lines: list[str], start_line: int, fence: str) -> int | None:
    """Return ending line for a fenced block."""

    for line_number in range(start_line + 1, len(lines) + 1):
        if lines[line_number - 1].lstrip().startswith(fence):
            return line_number
    return None


def _plain_block_kind(line: str) -> str | None:
    """Return supported plain Markdown block kind."""

    stripped = line.lstrip()
    if stripped.startswith(">"):
        return "blockquote"
    if stripped.startswith(("- ", "* ", "+ ")) or re.match(r"\d+\.\s+", stripped):
        return "list"
    if stripped.startswith("|") and stripped.endswith("|"):
        return "table"
    return "paragraph"


def _plain_block_end(lines: list[str], start_line: int) -> int:
    """Return inclusive ending line for a plain Markdown block."""

    for line_number in range(start_line + 1, len(lines) + 1):
        if not lines[line_number - 1].strip():
            return line_number - 1
    return len(lines)


def _finding(code: str, message: str, path: Path, line: int) -> Finding:
    """Return one Markdown parser finding."""

    return Finding(
        code=code,
        severity="error",
        message=message,
        locations=(LineSpan(path=path, start_line=line, end_line=line),),
    )
