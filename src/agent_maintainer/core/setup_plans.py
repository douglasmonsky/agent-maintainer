"""Side-effect-free setup target selection and preview rendering."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from agent_maintainer.core.scaffold.planning import InitAction, InitPlanItem
from agent_maintainer.core.scaffold.templates import StarterFile
from agent_maintainer.core.scaffold.transaction import apply_transaction


class SetupReviewError(ValueError):
    """Raised when a setup write is unreviewed, stale, or unconfined."""


@dataclass(frozen=True)
class ReviewedFileEdit:
    """One exact before/after file edit approved through a rendered diff."""

    path: str
    before: str | None
    after: str
    reason: str


def reviewed_edit_digest(edits: tuple[ReviewedFileEdit, ...]) -> str:
    """Return a deterministic digest binding paths and before/after content."""

    digest = hashlib.sha256()
    for edit in edits:
        digest.update(edit.path.encode())
        digest.update(b"\0")
        digest.update(b"<missing>" if edit.before is None else edit.before.encode())
        digest.update(b"\0")
        digest.update(edit.after.encode())
        digest.update(b"\0")
    return digest.hexdigest()


def render_reviewed_diff(edits: tuple[ReviewedFileEdit, ...]) -> str:
    """Render deterministic unified diffs for all reviewed setup edits."""

    return "".join(_render_edit_diff(edit) for edit in edits)


def apply_reviewed_edits(
    root: Path,
    edits: tuple[ReviewedFileEdit, ...],
    *,
    approved_digest: str,
) -> tuple[Path, ...]:
    """Apply a confined, unchanged reviewed edit set transactionally."""

    if approved_digest != reviewed_edit_digest(edits):
        raise SetupReviewError("approved digest does not match the displayed setup diff")
    canonical_root = root.resolve(strict=True)
    items = tuple(_transaction_item(canonical_root, edit) for edit in edits)
    result = apply_transaction(items, target=canonical_root)
    return result.written


def _render_edit_diff(edit: ReviewedFileEdit) -> str:
    before_lines = () if edit.before is None else edit.before.splitlines(keepends=True)
    after_lines = edit.after.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{edit.path}",
            tofile=f"b/{edit.path}",
        )
    )


def _transaction_item(root: Path, edit: ReviewedFileEdit) -> InitPlanItem:
    relative = PurePosixPath(edit.path)
    if not edit.path or relative.is_absolute() or ".." in relative.parts:
        raise SetupReviewError(f"setup path is not repository-confined: {edit.path}")
    destination = (root / edit.path).resolve(strict=False)
    if not destination.is_relative_to(root):
        raise SetupReviewError(f"setup path escapes repository: {edit.path}")
    current = _current_text(destination)
    if current != edit.before:
        raise SetupReviewError(f"setup source changed after review: {edit.path}")
    action = InitAction.ADD if edit.before is None else InitAction.MERGE
    starter = StarterFile(edit.path, edit.after, ("reviewed-setup",))
    return InitPlanItem(starter, destination, action, edit.after, edit.reason)


def _current_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SetupReviewError(f"cannot safely read setup path {path.name}: {exc}") from exc


def selected_root(target: Path | None, *, discovered: Path) -> Path:
    """Return an explicit repository root or the discovered current project."""

    return discovered if target is None else target.resolve()


def print_bootstrap_plan(
    repo_root: Path,
    dependency_file: Path,
    *,
    local_source: bool,
) -> None:
    """Print dependency-only bootstrap actions."""

    virtualenv = repo_root / ".venv"
    print(f"would ensure virtualenv: {virtualenv}")
    print(f"would install dependencies from: {dependency_file}")
    if local_source:
        print(f"would install editable package: {repo_root}")
    print("hooks are not installed by bootstrap; run `agent-maintainer install` explicitly")


def preview_pre_commit(repo_root: Path) -> int:
    """Print the pre-commit integration action without executing it."""

    if (repo_root / ".pre-commit-config.yaml").exists():
        print(f"would install pre-commit hook in {repo_root}")
    else:
        print("would skip pre-commit: .pre-commit-config.yaml not present")
    return 0
