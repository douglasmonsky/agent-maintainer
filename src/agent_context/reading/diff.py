"""Bounded Git diff context helpers."""

from __future__ import annotations

from dataclasses import dataclass

from agent_context.budget import bound_text
from agent_context.models import ContextBudget
from agent_context.reading.diff_classify import (
    count_matching,
    is_docs_path,
    is_generated_or_lock_path,
    is_python_path,
    is_test_path,
)
from agent_context.reading.diff_git import (
    DiffRequest,
    FileChange,
    changed_paths,
    file_changes,
    git_diff,
    name_status_lines,
)

DEFAULT_DIFF_HUNKS = 5


@dataclass(frozen=True)
class DiffResult:
    """Rendered bounded diff context."""

    text: str
    omitted_paths: int = 0
    omitted_hunks: int = 0
    truncated: bool = False


def render_diff(request: DiffRequest) -> DiffResult:
    """Return requested diff context."""

    if request.summary:
        return render_diff_summary(request)
    if request.name_only:
        return render_name_only(request)
    return render_patch(request)


def render_diff_summary(request: DiffRequest) -> DiffResult:
    """Return bounded diff summary."""

    paths = changed_paths(request)
    changes = file_changes(request)
    shown_paths = paths[: request.limit]
    omitted_paths = max(0, len(paths) - len(shown_paths))
    lines = [
        "Diff summary",
        f"files changed: {len(paths)}",
        f"Python files: {count_matching(paths, is_python_path)}",
        f"test files: {count_matching(paths, is_test_path)}",
        f"docs files: {count_matching(paths, is_docs_path)}",
        f"generated/lock files: {count_matching(paths, is_generated_or_lock_path)}",
        f"shown paths: {len(shown_paths)}",
        f"omitted paths: {omitted_paths}",
        "",
        "largest files by changed lines:",
        *largest_change_lines(changes),
        "",
        f"rename/move candidates: {rename_candidates(request)}",
        f"import-only candidates: {import_only_candidates(request, shown_paths)}",
        "",
        "expansion commands:",
        f"- python -m agent_maintainer context diff --name-only --limit {request.limit}",
        "- python -m agent_maintainer context diff --path <path>",
    ]
    return DiffResult(bound(lines_to_text(lines), request.budget), omitted_paths=omitted_paths)


def render_name_only(request: DiffRequest) -> DiffResult:
    """Return bounded changed path list."""

    paths = changed_paths(request)
    shown_paths = paths[: request.limit]
    omitted_paths = max(0, len(paths) - len(shown_paths))
    lines = [
        "Changed paths",
        *shown_paths,
        f"shown paths: {len(shown_paths)}",
        f"omitted paths: {omitted_paths}",
    ]
    return DiffResult(bound(lines_to_text(lines), request.budget), omitted_paths=omitted_paths)


def render_patch(request: DiffRequest) -> DiffResult:
    """Return bounded patch context."""

    patch = git_diff(request, path=request.path)
    selected, omitted_hunks = limit_hunks(patch, request.hunks or DEFAULT_DIFF_HUNKS)
    bounded = bound_text(selected, ContextBudget(max_chars=request.budget, max_items=1))
    return DiffResult(bounded.text, omitted_hunks=omitted_hunks, truncated=bounded.truncated)


def largest_change_lines(changes: tuple[FileChange, ...]) -> list[str]:
    """Return largest changed files lines."""

    largest = sorted(changes, key=lambda item: item.changed_lines, reverse=True)[:5]
    if not largest:
        return ["- none"]
    return [f"- {item.path}: {item.changed_lines}" for item in largest]


def rename_candidates(request: DiffRequest) -> int:
    """Return rename or move candidate count."""

    return sum(1 for line in name_status_lines(request) if line.startswith("R"))


def import_only_candidates(request: DiffRequest, paths: tuple[str, ...]) -> int:
    """Return count of Python files whose changed lines look import-only."""

    return sum(1 for path in paths if is_python_path(path) and patch_is_import_only(request, path))


def patch_is_import_only(request: DiffRequest, path: str) -> bool:
    """Return whether changed lines for path are import-only."""

    changed = [
        line[1:].strip()
        for line in git_diff(request, path=path).splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    return bool(changed) and all(line.startswith(("import ", "from ")) for line in changed)


def limit_hunks(patch: str, max_hunks: int) -> tuple[str, int]:
    """Return patch limited by number of hunks."""

    hunk_count = 0
    selected: list[str] = []
    omitted = 0
    for line in patch.splitlines():
        if line.startswith("@@"):
            hunk_count += 1
        if hunk_count <= max_hunks:
            selected.append(line)
        elif line.startswith("@@"):
            omitted += 1
    if omitted:
        selected.append(f"... omitted {omitted} diff hunks ...")
    return ("\n".join(selected), omitted)


def bound(text: str, budget: int) -> str:
    """Return char-bounded diff text."""

    return bound_text(text, ContextBudget(max_chars=budget, max_items=1)).text


def lines_to_text(lines: list[str]) -> str:
    """Return joined output lines."""

    return "\n".join(lines).rstrip()
