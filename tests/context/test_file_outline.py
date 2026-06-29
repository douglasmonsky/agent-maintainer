"""Tests safe Python file outline context."""

from __future__ import annotations

from typing import Any, cast

from agent_maintainer.context.reading.python_outline import build_outline

PYTHON_SAMPLE = '''@decorator
class Example:
    """Example docs."""

    def method(self):
        """Method docs."""
        return 1


def top_level():
    return Example()
'''


def test_ast_outline_extracts_classes_methods_and_decorators() -> None:
    """AST outline includes classes, methods, functions, and decorators."""

    outline = build_outline("sample.py", PYTHON_SAMPLE)

    names = [symbol.name for symbol in outline.symbols]
    assert names == ["Example", "Example.method", "top_level"]
    assert outline.symbols[0].decorators == ("decorator",)
    assert outline.symbols[0].docstring_line is not None


def test_outline_json_serializes_symbols() -> None:
    """Outline JSON includes nested symbol payloads."""

    payload = build_outline("sample.py", PYTHON_SAMPLE).to_json()
    symbols = cast(list[dict[str, Any]], payload["symbols"])

    assert payload["path"] == "sample.py"
    assert symbols[0]["name"] == "Example"


def test_ast_outline_handles_async_and_call_decorators() -> None:
    """AST outline handles async functions, async methods, and call decorators."""

    outline = build_outline(
        "async_sample.py",
        """@decorator()
async def fetch():
    return None

class AsyncExample:
    async def run(self):
        return None
""",
    )

    names = [symbol.name for symbol in outline.symbols]
    kinds = [symbol.kind for symbol in outline.symbols]
    assert names == ["fetch", "AsyncExample", "AsyncExample.run"]
    assert kinds == ["async function", "class", "async method"]
    assert outline.symbols[0].decorators == ("decorator",)


def test_ast_outline_handles_missing_docstrings() -> None:
    """Docstring line is absent when no docstring exists."""

    outline = build_outline("sample.py", "def no_docs():\n    return None\n")

    assert outline.symbols[0].docstring_line is None


def test_fallback_outline_handles_syntax_broken_python() -> None:
    """Fallback outline finds symbols even when syntax is broken."""

    outline = build_outline("broken.py", "def broken(:\n    pass\nclass Later:\n")

    assert outline.fallback is True
    assert "broken" in [symbol.name for symbol in outline.symbols]
    assert "Later" in [symbol.name for symbol in outline.symbols]
