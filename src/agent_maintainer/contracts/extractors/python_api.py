"""AST-only nominated Python public API extraction."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import cast

from agent_maintainer.contracts.limits import MAX_DEPTH, MAX_MEMBERS
from agent_maintainer.contracts.models import ContractSpec, Descriptor, ExtractionError
from agent_maintainer.contracts.normalization import (
    build_descriptor,
    safe_text,
    validate_json_value,
)
from agent_maintainer.contracts.paths import read_confined_text

type Definition = (
    ast.FunctionDef
    | ast.AsyncFunctionDef
    | ast.ClassDef
    | ast.Assign
    | ast.AnnAssign
)
type FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def extract_python_api(repo_root: Path, spec: ContractSpec) -> Descriptor:
    """Extract nominated public API facts without importing target code."""

    if spec.kind != "python-api":
        raise ExtractionError("Python extractor requires python-api kind")
    source = read_confined_text(repo_root, spec.source, label=f"contract {spec.id}")
    try:
        tree = ast.parse(source, filename=spec.source)
    except SyntaxError as exc:
        raise ExtractionError("Python source contains invalid syntax") from exc
    _validate_tree_bounds(tree)
    definitions, static_all, has_star_import = _module_definitions(tree)
    selected = _selected_names(spec, definitions, static_all, has_star_import)
    exports = [_normalize_definition(name, definitions[name]) for name in selected]
    return build_descriptor(spec, {"exports": exports})


def _validate_tree_bounds(tree: ast.AST) -> None:
    count = 0
    pending = [(tree, 0)]
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_MEMBERS:
            raise ExtractionError("Python AST must be bounded")
        if depth > MAX_DEPTH:
            raise ExtractionError("Python AST exceeds maximum depth")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))


def _module_definitions(
    tree: ast.Module,
) -> tuple[dict[str, Definition], tuple[str, ...] | None, bool]:
    definitions: dict[str, Definition] = {}
    static_all: tuple[str, ...] | None = None
    has_star_import = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            has_star_import = True
        if _changes_all(node):
            if static_all is not None:
                raise ExtractionError("duplicate __all__ definition")
            static_all = _static_all(node)
            continue
        named = _definition_name(node)
        if named is None:
            continue
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign),
        ):
            continue
        if named in definitions:
            raise ExtractionError(f"duplicate definition: {named}")
        definitions[named] = node
    return definitions, static_all, has_star_import


def _changes_all(node: ast.stmt) -> bool:
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return any(name == "__all__" for name in _assignment_names(node))
    return False


def _static_all(node: ast.stmt) -> tuple[str, ...]:
    value: ast.expr | None = None
    if isinstance(node, ast.Assign) and len(node.targets) != 1:
        raise ExtractionError("dynamic __all__ is unsupported")
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        value = node.value
    if not isinstance(value, (ast.List, ast.Tuple)):
        raise ExtractionError("dynamic __all__ is unsupported")
    names: list[str] = []
    for element in value.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            raise ExtractionError("dynamic __all__ is unsupported")
        names.append(safe_text(element.value, label="__all__ export"))
    if len(names) != len(set(names)):
        raise ExtractionError("duplicate __all__ export")
    return tuple(names)


def _assignment_names(node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> tuple[str, ...]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return tuple(target.id for target in targets if isinstance(target, ast.Name))


def _definition_name(node: ast.stmt) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        names = _assignment_names(node)
        if len(names) == 1:
            return names[0]
    return None


def _selected_names(
    spec: ContractSpec,
    definitions: dict[str, Definition],
    static_all: tuple[str, ...] | None,
    has_star_import: bool,
) -> tuple[str, ...]:
    if spec.exports == ("*",):
        if has_star_import:
            raise ExtractionError("star import cannot define public exports")
        candidates = (
            static_all
            if static_all is not None
            else tuple(name for name in definitions if not name.startswith("_"))
        )
    elif "*" in spec.exports:
        raise ExtractionError("wildcard export cannot overlap explicit names")
    else:
        candidates = spec.exports
    missing = sorted(set(candidates) - set(definitions))
    if missing:
        raise ExtractionError(f"missing export: {missing[0]}")
    return tuple(sorted(candidates))


def _normalize_definition(name: str, node: Definition) -> dict[str, object]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _normalize_function(node)
    if isinstance(node, ast.ClassDef):
        return _normalize_class(node)
    return _normalize_constant(name, node)


def _normalize_function(node: FunctionNode) -> dict[str, object]:
    return {
        "async": isinstance(node, ast.AsyncFunctionDef),
        "kind": "function",
        "name": safe_text(node.name, label="function name"),
        "parameters": _parameters(node.args),
        "return_annotation": _annotation_text(node.returns),
    }


def _parameters(arguments: ast.arguments) -> list[dict[str, object]]:
    positional = [*arguments.posonlyargs, *arguments.args]
    default_start = len(positional) - len(arguments.defaults)
    result = [
        _parameter(
            item,
            "positional-only" if index < len(arguments.posonlyargs) else "positional-or-keyword",
            index >= default_start,
        )
        for index, item in enumerate(positional)
    ]
    if arguments.vararg is not None:
        result.append(_parameter(arguments.vararg, "var-positional", False))
    result.extend(
        _parameter(item, "keyword-only", default is not None)
        for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True)
    )
    if arguments.kwarg is not None:
        result.append(_parameter(arguments.kwarg, "var-keyword", False))
    return result


def _parameter(argument: ast.arg, kind: str, has_default: bool) -> dict[str, object]:
    return {
        "annotation": _annotation_text(argument.annotation),
        "has_default": has_default,
        "kind": kind,
        "name": safe_text(argument.arg, label="parameter name"),
    }


def _normalize_class(node: ast.ClassDef) -> dict[str, object]:
    methods: list[dict[str, object]] = []
    attributes: list[dict[str, object]] = []
    identities: set[str] = set()
    for member in node.body:
        name = _definition_name(member)
        if name is None or name.startswith("_"):
            continue
        if name in identities:
            raise ExtractionError(f"duplicate class member: {name}")
        identities.add(name)
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_normalize_function(member))
        elif isinstance(member, (ast.Assign, ast.AnnAssign)):
            attributes.append(_normalize_attribute(name, member))
    methods.sort(key=lambda item: str(item["name"]))
    attributes.sort(key=lambda item: str(item["name"]))
    return {
        "attributes": attributes,
        "kind": "class",
        "methods": methods,
        "name": safe_text(node.name, label="class name"),
    }


def _normalize_constant(name: str, node: ast.Assign | ast.AnnAssign) -> dict[str, object]:
    value_node = node.value
    if value_node is None:
        raise ExtractionError(f"nominated constant must have a literal value: {name}")
    value = _literal_value(value_node, name=name)
    annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
    return {
        "annotation": _annotation_text(annotation),
        "kind": "constant",
        "name": safe_text(name, label="constant name"),
        "value": value,
    }


def _normalize_attribute(name: str, node: ast.Assign | ast.AnnAssign) -> dict[str, object]:
    value_node = node.value
    value = None if value_node is None else _literal_value(value_node, name=name)
    annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
    return {
        "annotation": _annotation_text(annotation),
        "default": value,
        "has_default": value_node is not None,
        "kind": "attribute",
        "name": safe_text(name, label="attribute name"),
    }


def _literal_value(value_node: ast.expr, *, name: str) -> object:
    try:
        value = ast.literal_eval(value_node)
    except (ValueError, TypeError) as exc:
        raise ExtractionError(f"nominated constant must have a literal value: {name}") from exc
    validate_json_value(value)
    return cast(object, value)


def _annotation_text(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    _validate_annotation(node)
    return ast.unparse(node)


def _validate_annotation(node: ast.AST) -> None:
    if isinstance(node, ast.Name):
        safe_text(node.id, label="annotation name")
    elif isinstance(node, ast.Attribute):
        safe_text(node.attr, label="annotation attribute")
        _validate_annotation(node.value)
    elif isinstance(node, ast.Subscript):
        _validate_annotation(node.value)
        _validate_annotation(node.slice)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            _validate_annotation(element)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        _validate_annotation(node.left)
        _validate_annotation(node.right)
    elif not _is_annotation_leaf(node):
        raise ExtractionError(f"unsupported annotation node: {type(node).__name__}")


def _is_annotation_leaf(node: ast.AST) -> bool:
    if isinstance(node, (ast.Load, ast.BitOr)):
        return True
    return isinstance(node, ast.Constant) and (
        node.value is None or isinstance(node.value, str)
    )
