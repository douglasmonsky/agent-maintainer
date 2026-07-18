"""Conservative affected-unit resolution across supported ecosystems."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.assess.models import PackageWorkspaceEvidence
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path
from agent_maintainer.ecosystems.git_changes import GitPathChange
from agent_maintainer.ecosystems.models import FileChangeClassification
from agent_maintainer.verification_plan.matching import (
    PathPatternError,
    validate_repo_pattern,
)
from agent_maintainer.verification_plan.models import AffectedUnit

MAX_WORKSPACE_ROOTS = 256
REPOSITORY_KEY = ("repository", "repository", ".")


@dataclass(frozen=True)
class UnitResolutionInputs:
    """Repository evidence required to resolve affected units."""

    config: MaintainerConfig
    classifications: tuple[FileChangeClassification, ...]
    package_workspace: PackageWorkspaceEvidence
    java_module_paths: tuple[str, ...]


@dataclass(frozen=True)
class _UnitRoots:
    python: tuple[str, ...]
    typescript: dict[str, str]
    java: tuple[str, ...]


def resolve_affected_units(
    repo_root: Path,
    *,
    changes: Sequence[GitPathChange],
    inputs: UnitResolutionInputs,
) -> tuple[tuple[AffectedUnit, ...], tuple[str, ...]]:
    """Return smallest-known units plus bounded ownership advisories."""
    advisories: list[str] = []
    roots = _UnitRoots(
        python=_validated_roots(
            inputs.config.package_paths,
            label="Python package root",
            advisories=advisories,
        ),
        java=_validated_roots(
            inputs.java_module_paths,
            label="Gradle module root",
            advisories=advisories,
        ),
        typescript=_typescript_workspace_roots(
            repo_root,
            inputs.package_workspace,
            advisories=advisories,
        ),
    )
    ecosystems = _ecosystems_by_path(inputs.classifications)
    grouped: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    affected_paths = sorted(
        {path for change in changes for path in change.affected_paths()},
    )
    for path in affected_paths:
        path_ecosystems = ecosystems.get(path, ())
        unit = _unit_for_path(
            path,
            path_ecosystems=path_ecosystems,
            roots=roots,
            advisories=advisories,
        )
        grouped[unit].add(path)
    units = tuple(
        AffectedUnit(kind=kind, name=name, root=root, changed_paths=tuple(sorted(paths)))
        for (kind, name, root), paths in sorted(grouped.items(), key=_unit_sort_key)
    )
    return units, tuple(sorted(set(advisories)))


def _unit_for_path(
    path: str,
    *,
    path_ecosystems: tuple[str, ...],
    roots: _UnitRoots,
    advisories: list[str],
) -> tuple[str, str, str]:
    if len(path_ecosystems) > 1:
        advisories.append(
            f"ambiguous ecosystem ownership for {path}: {', '.join(path_ecosystems)}",
        )
        return REPOSITORY_KEY
    if not path_ecosystems:
        return REPOSITORY_KEY
    ecosystem = path_ecosystems[0]
    unit = _owned_unit(path, ecosystem=ecosystem, roots=roots)
    if unit is not None:
        return unit
    if ecosystem not in {"java", "python", "typescript"}:
        return REPOSITORY_KEY
    advisories.append(f"no {ecosystem} unit owns changed path {path}; using repository")
    return REPOSITORY_KEY


def _owned_unit(
    path: str,
    *,
    ecosystem: str,
    roots: _UnitRoots,
) -> tuple[str, str, str] | None:
    if ecosystem == "python":
        root = _longest_root(path, roots.python)
        if root is not None:
            return ("python-package", root.rsplit("/", maxsplit=1)[-1], root)
    if ecosystem == "typescript":
        root = _longest_root(path, tuple(roots.typescript))
        if root is not None:
            return ("typescript-workspace", roots.typescript[root], root)
    if ecosystem == "java":
        root = _longest_root(path, roots.java)
        if root is not None:
            return ("gradle-module", root.rsplit("/", maxsplit=1)[-1], root)
    return None


def _validated_roots(
    roots: Sequence[str],
    *,
    label: str,
    advisories: list[str],
) -> tuple[str, ...]:
    validated: set[str] = set()
    for root in roots:
        try:
            validated.add(validate_repo_path(root, label=label))
        except RepoPathError as exc:
            advisories.append(f"ignored {label.lower()} {root!r}: {exc}")
    return tuple(sorted(validated))


def _typescript_workspace_roots(
    repo_root: Path,
    evidence: PackageWorkspaceEvidence,
    *,
    advisories: list[str],
) -> dict[str, str]:
    resolved_root = repo_root.resolve()
    roots: dict[str, str] = {}
    patterns = _workspace_patterns(evidence, advisories=advisories)
    for candidate in _bounded_workspace_candidates(
        repo_root,
        patterns,
        advisories=advisories,
    ):
        workspace = _workspace_root(
            repo_root,
            resolved_root,
            candidate,
            advisories=advisories,
        )
        if workspace is None:
            continue
        safe_root, name = workspace
        roots.setdefault(safe_root, name)
    return dict(sorted(roots.items()))


def _workspace_patterns(
    evidence: PackageWorkspaceEvidence,
    *,
    advisories: list[str],
) -> tuple[str, ...]:
    patterns: list[str] = []
    for declaration in evidence.workspace_declarations:
        for pattern in declaration.patterns:
            try:
                patterns.append(
                    validate_repo_pattern(
                        pattern,
                        label=f"workspace pattern from {declaration.source_path}",
                    ),
                )
            except PathPatternError as exc:
                advisories.append(f"ignored workspace pattern {pattern!r}: {exc}")
    return tuple(patterns)


def _bounded_workspace_candidates(
    repo_root: Path,
    patterns: tuple[str, ...],
    *,
    advisories: list[str],
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for pattern in patterns:
        for candidate in repo_root.glob(pattern):
            candidates.append(candidate)
            if len(candidates) > MAX_WORKSPACE_ROOTS:
                advisories.append(
                    f"workspace expansion exceeded {MAX_WORKSPACE_ROOTS} candidates",
                )
                return tuple(candidates[:MAX_WORKSPACE_ROOTS])
    return tuple(candidates)


def _workspace_root(
    repo_root: Path,
    resolved_root: Path,
    candidate: Path,
    *,
    advisories: list[str],
) -> tuple[str, str] | None:
    if not candidate.is_dir() or not (candidate / "package.json").is_file():
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        advisories.append(f"ignored out-of-repository workspace {candidate}")
        return None
    relative = candidate.relative_to(repo_root).as_posix()
    try:
        safe_root = validate_repo_path(relative, label="workspace root")
    except RepoPathError as exc:
        advisories.append(f"ignored workspace root {relative!r}: {exc}")
        return None
    name = _package_name(
        candidate / "package.json",
        fallback=safe_root,
        advisories=advisories,
    )
    return safe_root, name


def _package_name(
    package_json: Path,
    *,
    fallback: str,
    advisories: list[str],
) -> str:
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        advisories.append(f"could not read workspace name from {fallback}: {exc}")
        return fallback
    name = payload.get("name") if isinstance(payload, dict) else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    return fallback


def _ecosystems_by_path(
    classifications: Sequence[FileChangeClassification],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for classification in classifications:
        grouped[classification.path].add(classification.ecosystem)
    return {path: tuple(sorted(values)) for path, values in grouped.items()}


def _longest_root(path: str, roots: tuple[str, ...]) -> str | None:
    path_parts = tuple(path.split("/"))
    matches = [
        root
        for root in roots
        if path_parts[: len(root.split("/"))] == tuple(root.split("/"))
    ]
    if not matches:
        return None
    return max(matches, key=lambda root: (len(root.split("/")), root))


def _unit_sort_key(
    item: tuple[tuple[str, str, str], set[str]],
) -> tuple[int, str, str]:
    kind, _, root = item[0]
    return (0 if kind == "repository" else 1, kind, root)
