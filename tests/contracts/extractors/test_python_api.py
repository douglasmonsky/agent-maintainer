"""AST-only nominated Python API contract extraction tests."""

from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.contracts.extractors import python_api
from agent_maintainer.contracts.extractors.python_api import extract_python_api
from agent_maintainer.contracts.models import ContractSpec, ExtractionError


def _spec(exports: tuple[str, ...] = ("*",)) -> ContractSpec:
    return ContractSpec(
        id="docsync-api",
        kind="python-api",
        owner="docsync.api",
        stability="beta",
        revision=1,
        source="src/public.py",
        exports=exports,
    )


def _write(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "src/public.py"
    path.parent.mkdir(exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _exports(
    tmp_path: Path,
    source: str,
    exports: tuple[str, ...] = ("*",),
) -> list[dict[str, object]]:
    _write(tmp_path, source)
    descriptor = extract_python_api(tmp_path, _spec(exports))
    return cast(list[dict[str, object]], descriptor.body["exports"])


def test_python_function_signature_is_normalized_without_import(tmp_path: Path) -> None:
    """Parameter kinds and annotations are parsed while module code stays inert."""
    sentinel = tmp_path / "imported.txt"
    exports = _exports(
        tmp_path,
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed')\n"
        "__all__ = ['fetch']\n"
        "@decorator(factory())\n"
        "def fetch(item: str, /, limit: int = 10, *items: str, "
        "strict: bool = False, **metadata: object) -> list[str]:\n"
        "    raise RuntimeError('must not execute')\n",
    )

    function = exports[0]
    parameters = cast(list[dict[str, object]], function["parameters"])
    assert function["name"] == "fetch"
    assert function["return_annotation"] == "list[str]"
    assert [item["kind"] for item in parameters] == [
        "positional-only",
        "positional-or-keyword",
        "var-positional",
        "keyword-only",
        "var-keyword",
    ]
    assert [item["has_default"] for item in parameters] == [False, True, False, True, False]
    assert not sentinel.exists()


def test_explicit_exports_include_async_class_and_literal_constant(tmp_path: Path) -> None:
    """Nominated top-level functions, classes, and JSON literals are normalized."""
    exports = _exports(
        tmp_path,
        "PRIVATE = 'ignored'\n"
        "ANSWER: int = 42\n"
        "async def run(value: str | None = None) -> None:\n"
        "    pass\n"
        "class Client:\n"
        "    VERSION: str = 'v1'\n"
        "    required: str\n"
        "    _secret = 1\n"
        "    async def fetch(self, key: str) -> bytes:\n"
        "        pass\n",
        ("Client", "run", "ANSWER"),
    )

    assert [item["name"] for item in exports] == ["ANSWER", "Client", "run"]
    assert exports[0] == {
        "annotation": "int",
        "kind": "constant",
        "name": "ANSWER",
        "value": 42,
    }
    methods = cast(list[dict[str, object]], exports[1]["methods"])
    attributes = cast(list[dict[str, object]], exports[1]["attributes"])
    assert methods[0]["name"] == "fetch"
    assert methods[0]["async"] is True
    assert attributes == [
        {
            "annotation": "str",
            "default": "v1",
            "has_default": True,
            "kind": "attribute",
            "name": "VERSION",
        },
        {
            "annotation": "str",
            "default": None,
            "has_default": False,
            "kind": "attribute",
            "name": "required",
        },
    ]
    assert exports[2]["async"] is True


def test_wildcard_without_all_selects_only_public_top_level_names(tmp_path: Path) -> None:
    """Wildcard discovery excludes private and nested definitions."""
    exports = _exports(
        tmp_path,
        "def visible():\n    def nested():\n        pass\ndef _private():\n    pass\n",
    )

    assert [item["name"] for item in exports] == ["visible"]


def test_static_empty_all_exports_nothing(tmp_path: Path) -> None:
    """An explicit empty public API does not fall back to public-name discovery."""
    exports = _exports(tmp_path, "__all__ = []\ndef visible():\n    pass\n")

    assert exports == []


def test_python_exports_are_source_order_independent(tmp_path: Path) -> None:
    """Top-level declaration order does not change semantic evidence."""
    first = _exports(tmp_path, "def z():\n    pass\ndef a():\n    pass\n")
    second = _exports(tmp_path, "def a():\n    pass\ndef z():\n    pass\n")

    assert first == second
    assert [item["name"] for item in first] == ["a", "z"]


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("def broken(:\n    pass\n", "syntax"),
        ("names = ['run']\n__all__ = names\ndef run():\n    pass\n", "dynamic __all__"),
        ("from dependency import *\n", "star import"),
        ("def same():\n    pass\ndef same():\n    pass\n", "duplicate definition"),
        ("def unsafe(value: factory()) -> str:\n    pass\n", "annotation"),
    ),
)
def test_python_rejects_ambiguous_or_unsafe_ast(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    """Ambiguous export discovery and executable annotation shapes fail closed."""
    _write(tmp_path, source)

    with pytest.raises(ExtractionError, match=message):
        extract_python_api(tmp_path, _spec())


def test_python_rejects_computed_nominated_constant(tmp_path: Path) -> None:
    """Significant constants are literal data and are never evaluated."""
    _write(tmp_path, "ANSWER = 40 + 2\n")

    with pytest.raises(ExtractionError, match="literal"):
        extract_python_api(tmp_path, _spec(("ANSWER",)))


def test_python_rejects_missing_nominated_export(tmp_path: Path) -> None:
    """Explicit policy names cannot silently disappear from the source module."""
    _write(tmp_path, "def present():\n    pass\n")

    with pytest.raises(ExtractionError, match="missing export: absent"):
        extract_python_api(tmp_path, _spec(("absent",)))


def test_python_enforces_ast_member_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """AST traversal is bounded before semantic normalization."""
    monkeypatch.setattr(python_api, "MAX_MEMBERS", 2)
    _write(tmp_path, "def visible(value: str):\n    pass\n")

    with pytest.raises(ExtractionError, match="bounded"):
        extract_python_api(tmp_path, _spec())
