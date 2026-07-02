"""Bounded file context expansion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_context.budget import bound_text
from agent_context.failures import DEFAULT_CONTEXT_BUDGET
from agent_context.models import ContextBudget
from agent_context.reading.file_safety import FileSafety, inspect_file
from agent_context.reading.python_outline import (
    PythonOutline,
    SymbolOutline,
    build_outline,
)

DEFAULT_FILE_CONTEXT_LINES = 40


@dataclass(frozen=True)
class FileRequest:
    """Requested file context selection."""

    path: Path
    outline: bool = False
    symbols: bool = False
    symbol: str | None = None
    line_range: str | None = None
    around: int | None = None
    context_lines: int = DEFAULT_FILE_CONTEXT_LINES
    budget: int = DEFAULT_CONTEXT_BUDGET


@dataclass(frozen=True)
class FileContext:
    """Selected file context."""

    path: Path
    mode: str
    text: str
    refused: bool
    reason: str
    start_line: int | None
    end_line: int | None
    original_chars: int
    selected_chars: int
    omitted_chars: int
    outline: PythonOutline | None = None

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "path": str(self.path),
            "mode": self.mode,
            "text": self.text,
            "refused": self.refused,
            "reason": self.reason,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "original_chars": self.original_chars,
            "selected_chars": self.selected_chars,
            "omitted_chars": self.omitted_chars,
            "outline": self.outline.to_json() if self.outline else None,
        }


@dataclass(frozen=True)
class ContextSelection:
    """Intermediate selected file context before budget bounding."""

    request: FileRequest
    mode: str
    selected: str
    original: str
    line_bounds: tuple[int, int] | None = None
    outline: PythonOutline | None = None


def select_file_context(request: FileRequest) -> FileContext:
    """Return safe file context for request."""

    safety = inspect_file(request.path)
    if not safety.allowed:
        return refused_context(request.path, safety)
    text = request.path.read_text(encoding="utf-8")
    outline = outline_for_path(request.path, text)
    return selected_file_context(request, text, outline)


def selected_file_context(
    request: FileRequest,
    text: str,
    outline: PythonOutline | None,
) -> FileContext:
    """Return selected file context after safety checks."""

    if request.symbol:
        return symbol_context(request, text, outline)
    if request.line_range:
        return lines_context(
            request,
            text,
            parse_line_range(request.line_range, count_lines(text)),
        )
    if request.around is not None:
        return lines_context(
            request,
            text,
            around_range(request.around, request.context_lines, count_lines(text)),
        )
    if request.symbols:
        return symbols_context(request, text, outline)
    return outline_context(request, text, outline)


def refused_context(path: Path, safety: FileSafety) -> FileContext:
    """Return refused file context."""

    return FileContext(
        path,
        "refused",
        f"Refused file context: {safety.reason}",
        True,
        safety.reason,
        None,
        None,
        0,
        0,
        0,
    )


def outline_for_path(path: Path, text: str) -> PythonOutline | None:
    """Return Python outline when path looks like Python."""

    return build_outline(str(path), text) if path.suffix == ".py" else None


def outline_context(request: FileRequest, text: str, outline: PythonOutline | None) -> FileContext:
    """Return file outline context."""

    if outline is None:
        return bounded_context(
            ContextSelection(request, "outline", f"File lines: {count_lines(text)}", text),
        )
    return bounded_context(
        ContextSelection(request, "outline", render_outline(outline), text, outline=outline),
    )


def symbols_context(request: FileRequest, text: str, outline: PythonOutline | None) -> FileContext:
    """Return symbol list context."""

    symbols = () if outline is None else outline.symbols
    body = "\n".join(symbol.name for symbol in symbols) or "No symbols found."
    return bounded_context(ContextSelection(request, "symbols", body, text, outline=outline))


def symbol_context(request: FileRequest, text: str, outline: PythonOutline | None) -> FileContext:
    """Return source for one named symbol."""

    symbol = find_symbol(outline, request.symbol or "")
    if symbol is None:
        return bounded_context(
            ContextSelection(
                request,
                "symbol",
                f"Symbol not found: {request.symbol}",
                text,
                outline=outline,
            ),
        )
    return lines_context(
        request,
        text,
        (symbol.start_line, symbol.end_line),
        mode="symbol",
        outline=outline,
    )


def lines_context(
    request: FileRequest,
    text: str,
    line_bounds: tuple[int, int],
    *,
    mode: str = "lines",
    outline: PythonOutline | None = None,
) -> FileContext:
    """Return selected source lines."""

    start_line, end_line = line_bounds
    lines = text.splitlines()
    offset = start_line - 1
    selected = "\n".join(lines[offset:end_line])
    return bounded_context(
        ContextSelection(request, mode, selected, text, (start_line, end_line), outline),
    )


def bounded_context(selection: ContextSelection) -> FileContext:
    """Return bounded file context."""

    bounded = bound_text(
        selection.selected,
        ContextBudget(max_chars=selection.request.budget, max_items=1),
    )
    start_line, end_line = selection.line_bounds or (None, None)
    return FileContext(
        path=selection.request.path,
        mode=selection.mode,
        text=bounded.text,
        refused=False,
        reason="ok",
        start_line=start_line,
        end_line=end_line,
        original_chars=len(selection.original),
        selected_chars=len(bounded.text),
        omitted_chars=bounded.omitted_chars,
        outline=selection.outline,
    )


def render_outline(outline: PythonOutline) -> str:
    """Return readable outline text."""

    lines = [
        f"Python outline: {outline.path}",
        f"fallback: {outline.fallback}",
        f"lines: {outline.line_count}",
    ]
    for symbol in outline.symbols:
        lines.append(render_symbol(symbol))
    return "\n".join(lines)


def render_symbol(symbol: SymbolOutline) -> str:
    """Return one readable symbol line."""

    decorator_names = ",".join(symbol.decorators)
    decorators = f" decorators={decorator_names}" if symbol.decorators else ""
    docstring = f" docstring_line={symbol.docstring_line}" if symbol.docstring_line else ""
    return (
        f"- {symbol.kind} {symbol.name} "
        f"lines={symbol.start_line}:{symbol.end_line} "
        f"count={symbol.line_count}{decorators}{docstring}"
    )


def find_symbol(outline: PythonOutline | None, name: str) -> SymbolOutline | None:
    """Return symbol by exact name."""

    if outline is None:
        return None
    return next((symbol for symbol in outline.symbols if symbol.name == name), None)


def parse_line_range(line_range: str, total_lines: int) -> tuple[int, int]:
    """Parse one-based inclusive line range."""

    start_raw, end_raw = line_range.split(":", maxsplit=1)
    start = max(1, int(start_raw))
    end = min(max(start, int(end_raw)), total_lines)
    return (start, end)


def around_range(line_number: int, context_lines: int, total_lines: int) -> tuple[int, int]:
    """Return around-line one-based inclusive bounds."""

    start = max(1, line_number - context_lines)
    end = min(total_lines, line_number + context_lines)
    return (start, end)


def count_lines(text: str) -> int:
    """Return display line count."""

    return len(text.splitlines()) if text else 0


def render_file_text(context: FileContext) -> str:
    """Return text file context report."""

    header = [
        f"Context file: {context.path}",
        f"Mode: {context.mode}",
        f"Refused: {context.refused}",
    ]
    if context.start_line is not None and context.end_line is not None:
        header.append(f"Lines: {context.start_line}:{context.end_line}")
    header.extend(("", context.text))
    return "\n".join(header).rstrip()


def render_file_json(context: FileContext) -> str:
    """Return JSON file context report."""

    return json.dumps(context.to_json(), indent=2, sort_keys=True)
