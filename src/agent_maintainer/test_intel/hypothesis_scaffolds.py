"""Advisory Hypothesis scaffold text generation."""

from __future__ import annotations

import ast
import re

NUMERIC_TYPES = frozenset(("float", "int"))
STRING_TYPES = frozenset(("str",))
SAFE_IDENTIFIER_PATTERN = re.compile(r"[^0-9a-zA-Z_]+")


def scaffold_lines(qualname: str, node: ast.FunctionDef) -> tuple[str, ...]:
    """Return advisory Hypothesis scaffold lines for a function."""

    function_name = qualname.split(".")[-1]
    test_name = safe_test_name(function_name)
    required_args = required_argument_names(node)
    strategy = preferred_strategy(node)
    if len(required_args) == 1 and "." not in qualname:
        argument = required_args[0]
        return (
            f"@given({argument}={strategy})",
            f"def test_{test_name}_properties({argument}):",
            f"    result = {function_name}({argument})",
            "    assert result is not None",
        )
    return (
        "@given(data=st.data())",
        f"def test_{test_name}_properties(data):",
        "    # TODO: draw inputs that match the function contract.",
        f"    result = {function_name}(...)",
        "    assert result is not None",
    )


def required_argument_names(node: ast.FunctionDef) -> tuple[str, ...]:
    """Return positional arguments without defaults."""

    positional_args = tuple(arg.arg for arg in (*node.args.posonlyargs, *node.args.args))
    default_count = len(node.args.defaults)
    required_count = max(len(positional_args) - default_count, 0)
    names = positional_args[:required_count]
    if names and names[0] in {"cls", "self"}:
        return names[1:]
    return names


def preferred_strategy(node: ast.FunctionDef) -> str:
    """Return a starting Hypothesis strategy for the first required argument."""

    required_args = (*node.args.posonlyargs, *node.args.args)
    if required_args:
        annotation = required_args[0].annotation
        annotation_name = annotation_text(annotation)
        if annotation_name in NUMERIC_TYPES:
            return "st.integers(min_value=-1000, max_value=1000)"
        if annotation_name in STRING_TYPES:
            return "st.text()"
    return "st.data()"


def annotation_text(annotation: ast.expr | None) -> str:
    """Return normalized annotation text."""

    if annotation is None:
        return ""
    return ast.unparse(annotation).lower()


def safe_test_name(function_name: str) -> str:
    """Return safe pytest function-name suffix."""

    cleaned = SAFE_IDENTIFIER_PATTERN.sub("_", function_name).strip("_").lower()
    return cleaned or "candidate"
