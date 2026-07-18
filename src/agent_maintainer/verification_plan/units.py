"""Conservative affected-unit resolution across supported ecosystems."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from agent_maintainer.assess import models as assess_models
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.core import repo_paths
from agent_maintainer.ecosystems import git_changes
from agent_maintainer.ecosystems import models as ecosystem_models
from agent_maintainer.verification_plan import matching
from agent_maintainer.verification_plan import models as plan_models

MAX_WORKSPACE_ROOTS = 256
REPOSITORY_KEY = ("repository", "repository", ".")


@dataclass(frozen=True)
class UnitResolutionInputs:
    """Repository evidence required to resolve affected units."""

    config: MaintainerConfig
    classifications: tuple[ecosystem_models.FileChangeClassification, ...]
    package_workspace: assess_models.PackageWorkspaceEvidence
    java_module_paths: tuple[str, ...]


@dataclass(frozen=True)
class _UnitRoots:
    python: tuple[str, ...]
    typescript: dict[str, str]
    java: tuple[str, ...]


def resolve_affected_units(
    repo_root: Path,
    *,
    changes: tuple[git_changes.GitPathChange, ...],
    inputs: UnitResolutionInputs,
) -> tuple[tuple[plan_models.AffectedUnit, ...], tuple[str, ...]]:
    """Return smallest-known units plus bounded ownership advisories."""
    advisories: list[str] = []
    roots = _build_roots(repo_root, inputs, advisories=advisories)
    grouped = _group_paths(changes, inputs.classifications, roots, advisories=advisories)
    units = tuple(
        plan_models.AffectedUnit(
            kind=kind,
            name=name,
            root=root,
            changed_paths=tuple(sorted(paths)),
        )
        for (kind, name, root), paths in sorted(grouped.items(), key=_unit_sort_key)
    )
    return units, tuple(sorted(set(advisories)))


def _build_roots(
    repo_root: Path,
    inputs: UnitResolutionInputs,
    *,
    advisories: list[str],
) -> _UnitRoots:
    return _UnitRoots(
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


def _group_paths(
    changes: tuple[git_changes.GitPathChange, ...],
    classifications: tuple[ecosystem_models.FileChangeClassification, ...],
    roots: _UnitRoots,
    *,
    advisories: list[str],
) -> dict[tuple[str, str, str], set[str]]:
    ecosystems = _ecosystems_by_path(classifications)
    grouped: dict[tuple[str, str, str], set[str]] = {}
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
        grouped.setdefault(unit, set()).add(path)
    return grouped


def _unit_for_path(
    path: str,
    *,
    path_ecosystems: tuple[str, ...],
    roots: _UnitRoots,
    advisories: list[str],
) -> tuple[str, str, str]:
    if len(path_ecosystems) > 1:
        ecosystems = ", ".join(path_ecosystems)
        advisories.append(f"ambiguous ecosystem ownership for {path}: {ecosystems}")
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
    roots: tuple[str, ...],
    *,
    label: str,
    advisories: list[str],
) -> tuple[str, ...]:
    validated: set[str] = set()
    for root in roots:
        try:
            validated.add(repo_paths.validate_repo_path(root, label=label))
        except repo_paths.RepoPathError as exc:
            advisories.append(f"ignored {label.lower()} {root!r}: {exc}")
    return tuple(sorted(validated))


def _typescript_workspace_roots(
    repo_root: Path,
    evidence: assess_models.PackageWorkspaceEvidence,
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
    evidence: assess_models.PackageWorkspaceEvidence,
    *,
    advisories: list[str],
) -> tuple[str, ...]:
    patterns: list[str] = []
    for declaration in evidence.workspace_declarations:
        for pattern in declaration.patterns:
            try:
                patterns.append(
                    matching.validate_repo_pattern(
                        pattern,
                        label=f"workspace pattern from {declaration.source_path}",
                    ),
                )
            except matching.PathPatternError as exc:
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
    manifest = candidate / "package.json"
    if not candidate.is_dir() or not manifest.is_file():
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        advisories.append(f"ignored out-of-repository workspace {candidate}")
        return None
    if not manifest.resolve().is_relative_to(resolved_root):
        advisories.append(f"ignored workspace manifest outside repository: {manifest}")
        return None
    relative = candidate.relative_to(repo_root).as_posix()
    try:
        safe_root = repo_paths.validate_repo_path(relative, label="workspace root")
    except repo_paths.RepoPathError as exc:
        advisories.append(f"ignored workspace root {relative!r}: {exc}")
        return None
    name = _package_name(
        manifest,
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
    package = cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    name = package.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return fallback


def _ecosystems_by_path(
    classifications: tuple[ecosystem_models.FileChangeClassification, ...],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, set[str]] = {}
    for classification in classifications:
        grouped.setdefault(classification.path, set()).add(classification.ecosystem)
    return {path: tuple(sorted(values)) for path, values in grouped.items()}


def _longest_root(path: str, roots: tuple[str, ...]) -> str | None:
    path_parts = tuple(path.split("/"))
    matches = [
        root for root in roots if path_parts[: len(root.split("/"))] == tuple(root.split("/"))
    ]
    if not matches:
        return None
    return max(matches, key=lambda root: (len(root.split("/")), root))


def _unit_sort_key(
    item: tuple[tuple[str, str, str], set[str]],
) -> tuple[int, str, str]:
    kind, _, root = item[0]
    return (0 if kind == "repository" else 1, kind, root)
