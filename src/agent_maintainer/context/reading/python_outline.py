"""Compatibility shim for Python outline context readers."""

from agent_context.reading import python_outline

CHUNK_LINE_COUNT = python_outline.CHUNK_LINE_COUNT
SYMBOL_PATTERN = python_outline.SYMBOL_PATTERN
PythonOutline = python_outline.PythonOutline
SymbolOutline = python_outline.SymbolOutline
ast_symbols = python_outline.ast_symbols
build_outline = python_outline.build_outline
chunk_symbols = python_outline.chunk_symbols
class_method_symbols = python_outline.class_method_symbols
count_lines = python_outline.count_lines
decorator_name = python_outline.decorator_name
decorator_names = python_outline.decorator_names
docstring_line = python_outline.docstring_line
fallback_outline = python_outline.fallback_outline
fallback_symbol = python_outline.fallback_symbol
symbol_from_ast = python_outline.symbol_from_ast
