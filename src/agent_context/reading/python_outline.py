"""Python source outline extraction."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

CHUNK_LINE_COUNT = 80
SYMBOL_PATTERN = re.compile(r"^(?P<indent>\s*)(?P<kind>class|def|async def)\s+(?P<name>[\w_]+)")


@dataclass(frozen=True)
class SymbolOutline:
    """One Python symbol outline item."""

    name: str
    kind: str
    start_line: int
    end_line: int
    decorators: tuple[str, ...]
    docstring_line: int | None
    line_count: int

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "name": self.name,
            "kind": self.kind,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "decorators": list(self.decorators),
            "docstring_line": self.docstring_line,
            "line_count": self.line_count,
        }


@dataclass(frozen=True)
class PythonOutline:
    """Python file outline."""

    path: str
    symbols: tuple[SymbolOutline, ...]
    fallback: bool
    line_count: int

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "path": self.path,
            "fallback": self.fallback,
            "line_count": self.line_count,
            "symbols": [symbol.to_json() for symbol in self.symbols],
        }


def build_outline(path: str, text: str) -> PythonOutline:
    """Build Python outline from source text."""

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return fallback_outline(path, text)
    return PythonOutline(
        path=path,
        symbols=tuple(ast_symbols(tree)),
        fallback=False,
        line_count=count_lines(text),
    )


def ast_symbols(tree: ast.AST) -> tuple[SymbolOutline, ...]:
    """Return class and function symbols from AST."""

    symbols: list[SymbolOutline] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(symbol_from_ast(node, "class", node.name))
            symbols.extend(class_method_symbols(node))
        elif isinstance(node, ast.AsyncFunctionDef):
            symbols.append(symbol_from_ast(node, "async function", node.name))
        elif isinstance(node, ast.FunctionDef):
            symbols.append(symbol_from_ast(node, "function", node.name))
    return tuple(symbols)


def class_method_symbols(node: ast.ClassDef) -> tuple[SymbolOutline, ...]:
    """Return methods nested one level inside a class."""

    symbols: list[SymbolOutline] = []
    for child in node.body:
        if isinstance(child, ast.AsyncFunctionDef):
            symbols.append(
                symbol_from_ast(child, "async method", f"{node.name}.{child.name}"),
            )
        elif isinstance(child, ast.FunctionDef):
            symbols.append(symbol_from_ast(child, "method", f"{node.name}.{child.name}"))
    return tuple(symbols)


def symbol_from_ast(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    kind: str,
    name: str,
) -> SymbolOutline:
    """Return outline item from AST node."""

    start_line = node.lineno
    end_line = getattr(node, "end_lineno", node.lineno)
    return SymbolOutline(
        name=name,
        kind=kind,
        start_line=start_line,
        end_line=end_line,
        decorators=decorator_names(node.decorator_list),
        docstring_line=docstring_line(node),
        line_count=end_line - start_line + 1,
    )


def decorator_names(decorators: list[ast.expr]) -> tuple[str, ...]:
    """Return decorator source names."""

    return tuple(decorator_name(item) for item in decorators)


def decorator_name(node: ast.expr) -> str:
    """Return stable decorator display name."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return type(node).__name__


def docstring_line(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int | None:
    """Return docstring starting line when present."""

    if not node.body:
        return None
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return first.lineno if isinstance(first.value.value, str) else None
    return None


def fallback_outline(path: str, text: str) -> PythonOutline:
    """Return regex and chunk outline for syntax-broken Python."""

    lines = text.splitlines()
    symbols = [fallback_symbol(index, line) for index, line in enumerate(lines, start=1)]
    symbols.extend(chunk_symbols(lines))
    return PythonOutline(
        path,
        tuple(item for item in symbols if item is not None),
        True,
        len(lines),
    )


def fallback_symbol(line_number: int, line: str) -> SymbolOutline | None:
    """Return fallback symbol for a single line."""

    match = SYMBOL_PATTERN.match(line)
    if match is None:
        return None
    kind = "class" if match.group("kind") == "class" else "function"
    name = match.group("name")
    return SymbolOutline(name, kind, line_number, line_number, (), None, 1)


def chunk_symbols(lines: list[str]) -> tuple[SymbolOutline, ...]:
    """Return coarse line-count chunks for fallback navigation."""

    chunks: list[SymbolOutline] = []
    for start in range(1, len(lines) + 1, CHUNK_LINE_COUNT):
        end = min(start + CHUNK_LINE_COUNT - 1, len(lines))
        chunks.append(
            SymbolOutline(f"lines {start}-{end}", "chunk", start, end, (), None, end - start + 1),
        )
    return tuple(chunks)


def count_lines(text: str) -> int:
    """Return display line count."""

    return len(text.splitlines()) if text else 0
