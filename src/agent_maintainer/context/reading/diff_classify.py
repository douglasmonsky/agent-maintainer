"""Path classification helpers for diff context."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

LOCK_FILE_NAMES = frozenset(("package-lock.json", "pnpm-lock.yaml", "poetry.lock", "uv.lock"))
GENERATED_PARTS = frozenset(("generated", "__pycache__", "node_modules", ".venv", "venv"))
DOC_SUFFIXES = frozenset((".md", ".rst", ".txt"))
PYTHON_SUFFIX = ".py"


def count_matching(paths: tuple[str, ...], predicate: Callable[[str], bool]) -> int:
    """Return count of paths matching predicate."""

    return sum(1 for path in paths if predicate(path))


def is_python_path(path: str) -> bool:
    """Return whether path is Python source."""

    return path.endswith(PYTHON_SUFFIX)


def is_test_path(path: str) -> bool:
    """Return whether path is a test path."""

    return path.startswith("tests/") or "/test_" in path or path.endswith("_test.py")


def is_docs_path(path: str) -> bool:
    """Return whether path is documentation."""

    return Path(path).suffix in DOC_SUFFIXES or path.startswith("docs/")


def is_generated_or_lock_path(path: str) -> bool:
    """Return whether path looks generated or lock-like."""

    file_path = Path(path)
    return file_path.name in LOCK_FILE_NAMES or any(
        part in GENERATED_PARTS for part in file_path.parts
    )
