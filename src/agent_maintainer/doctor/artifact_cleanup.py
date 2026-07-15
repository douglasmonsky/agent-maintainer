"""Plan and apply safe generated-artifact cleanup."""

from __future__ import annotations

import shutil
from pathlib import Path

BYTECODE_ROOTS = ("src", "tests", ".codex/hooks", ".claude/hooks")
DUPLICATE_GENERATED_ROOTS = (".verify-logs", "build", "dist")


def artifact_cleanup_plan(repo_root: Path) -> tuple[Path, ...]:
    """Return generated paths eligible for explicit cleanup."""

    root = repo_root.resolve()
    duplicate_files = generated_duplicate_files(root)
    bytecode_paths = generated_bytecode_paths(root)
    return tuple((*duplicate_files, *bytecode_paths))


def prune_generated_artifacts(
    repo_root: Path,
    *,
    apply: bool,
) -> tuple[Path, ...]:
    """Return or apply the safe cleanup plan."""

    plan = artifact_cleanup_plan(repo_root)
    if not apply:
        return plan
    removed: list[Path] = []
    root = repo_root.resolve()
    for path in plan:
        if not safe_generated_path(root, path):
            continue
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            continue
        removed.append(path)
    return tuple(removed)


def generated_duplicate_files(repo_root: Path) -> tuple[Path, ...]:
    """Return duplicate-named files only from known generated roots."""

    candidates: list[Path] = []
    for relative in DUPLICATE_GENERATED_ROOTS:
        generated_root = repo_root / relative
        if not safe_generated_root(repo_root, generated_root):
            continue
        candidates.extend(
            path
            for path in generated_root.rglob("*")
            if path.is_file()
            and is_duplicate_named_artifact(path)
            and safe_generated_path(repo_root, path)
        )
    return tuple(sorted(candidates))


def generated_bytecode_paths(repo_root: Path) -> tuple[Path, ...]:
    """Return bytecode directories and standalone files from owned roots."""

    source_roots = tuple(
        path
        for relative in BYTECODE_ROOTS
        if safe_generated_root(repo_root, path := repo_root / relative)
    )
    directories = {
        path
        for source_root in source_roots
        for path in source_root.rglob("__pycache__")
        if path.is_dir() and safe_generated_path(repo_root, path)
    }
    standalone_files = {
        path
        for source_root in source_roots
        for path in source_root.rglob("*.pyc")
        if standalone_bytecode_file(repo_root, path, directories)
    }
    return tuple((*sorted(directories), *sorted(standalone_files)))


def standalone_bytecode_file(
    repo_root: Path,
    path: Path,
    bytecode_directories: set[Path],
) -> bool:
    """Return whether a bytecode file is outside a planned cache directory."""

    return (
        path.is_file()
        and not any(parent in bytecode_directories for parent in path.parents)
        and safe_generated_path(repo_root, path)
    )


def safe_generated_root(repo_root: Path, path: Path) -> bool:
    """Return whether an existing generated root is local and not symlinked."""

    return path.exists() and path.is_dir() and safe_generated_path(repo_root, path)


def safe_generated_path(repo_root: Path, path: Path) -> bool:
    """Return whether a candidate stays below root without symlink traversal."""

    try:
        relative = path.relative_to(repo_root)
    except ValueError:
        return False
    current = repo_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return False
    try:
        path.resolve().relative_to(repo_root)
    except (OSError, ValueError):
        return False
    return True


def is_duplicate_or_bytecode_artifact(path: Path) -> bool:
    """Return whether a path looks like duplicate or bytecode debris."""

    return is_duplicate_named_artifact(path) or path.name == "__pycache__" or path.suffix == ".pyc"


def is_duplicate_named_artifact(path: Path) -> bool:
    """Return whether a filename looks like an accidental Finder-style copy."""

    name = path.name.lower()
    return any(pattern in name for pattern in (" 2", " copy", " - copy"))
