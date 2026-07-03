"""Architecture decision-note enforcement for policy changes."""

from __future__ import annotations

import fnmatch
import re
from datetime import UTC, datetime
from pathlib import Path

from archguard.git_diff import changed_paths
from archguard.models import ArchitecturePolicyChange

# docsync:evidence.start evidence.architecture.decision_notes
DEFAULT_DECISION_ROOTS = ("docs/architecture/decisions", ".archguard/decisions")
DEFAULT_POLICY_PATTERNS = ("tach.toml", "tach.domain.toml", "**/tach.domain.toml")
SLUG_RE = re.compile(r"[^a-z0-9._-]+")


def decision_check_failures(
    repo_root: Path,
    *,
    base_ref: str,
    staged: bool,
    decision_roots: tuple[str, ...] = DEFAULT_DECISION_ROOTS,
    policy_patterns: tuple[str, ...] = DEFAULT_POLICY_PATTERNS,
) -> list[str]:
    """Return decision-note failures for changed architecture policy files."""
    try:
        paths = changed_paths(repo_root, base_ref=base_ref, staged=staged)
    except RuntimeError as exc:
        return [str(exc)]

    policy_paths = tuple(path for path in paths if is_policy_path(path, policy_patterns))
    if not policy_paths:
        return []
    if any(is_decision_note_path(path, decision_roots) for path in paths):
        return []

    change = ArchitecturePolicyChange(policy_paths)
    return [
        f"architecture policy changed without decision note: {change.format_paths()}",
        "Add or update a decision note under docs/architecture/decisions/.",
    ]


# docsync:evidence.end evidence.architecture.decision_notes


def is_policy_path(path: str, policy_patterns: tuple[str, ...]) -> bool:
    """Return whether a changed path is architecture policy."""
    normalized = normalize_repo_path(path)
    return any(matches_pattern(normalized, pattern) for pattern in policy_patterns)


def normalize_repo_path(path: str) -> str:
    """Return repository-relative path text without stripping dot directories."""

    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def matches_pattern(path: str, pattern: str) -> bool:
    """Return whether a normalized path matches an architecture policy pattern."""
    normalized = normalize_repo_path(pattern)
    return (
        path == normalized
        or fnmatch.fnmatch(path, normalized)
        or fnmatch.fnmatch(path, f"**/{normalized}")
    )


def is_decision_note_path(path: str, decision_roots: tuple[str, ...]) -> bool:
    """Return whether a changed path is a Markdown decision note."""
    normalized = normalize_repo_path(path)
    if not normalized.endswith(".md"):
        return False
    return any(
        normalized == normalized_decision_root(root)
        or normalized.startswith(f"{normalized_decision_root(root)}/")
        for root in decision_roots
    )


def new_decision_note(repo_root: Path, slug: str, *, decision_root: str) -> Path:
    """Create a dated architecture decision note and return its path."""
    clean_slug = normalize_slug(slug)
    root = repo_root / decision_root
    root.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=UTC).date().isoformat()
    path = root / f"{today}-{clean_slug}.md"
    if path.exists():
        return path
    path.write_text(decision_template(clean_slug), encoding="utf-8")
    return path


def normalize_slug(value: str) -> str:
    """Normalize user input into a decision-note slug."""
    slug = SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "architecture-decision"


def normalized_decision_root(value: str) -> str:
    """Normalize a decision note root for path comparisons."""
    return normalize_repo_path(value)


def decision_template(slug: str) -> str:
    """Return the starter content for a new architecture decision note."""
    title = slug.replace("-", " ").replace("_", " ").title()
    return f"""# Architecture Decision: {title}

Status: proposed

## What changed?

Describe the Tach architecture-policy change.

## Why was this necessary?

Explain the concrete requirement that made the boundary change necessary.

## Why is this not just architecture drift?

Explain why the change preserves or improves architecture quality.

## Alternatives considered

1. Keep the existing boundary unchanged.
2. Refactor implementation code instead of changing policy.

## Boundary impact

State which modules, layers, or dependency rules changed.

## What remains forbidden?

State what agents and maintainers should still avoid.

## Review or expiration condition

State when this decision should be revisited, removed, or tightened.
"""
