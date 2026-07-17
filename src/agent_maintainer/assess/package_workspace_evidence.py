"""Advisory package-manager and workspace evidence collection."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yaml

from agent_maintainer.assess.models import (
    PackageManagerSignal,
    PackageWorkspaceEvidence,
    PackageWorkspaceIssue,
    WorkspaceDeclaration,
)

SUPPORTED_MANAGERS = frozenset(("npm", "pnpm", "yarn", "bun"))
LOCKFILE_MANAGERS = (
    ("bun.lock", "bun"),
    ("bun.lockb", "bun"),
    ("npm-shrinkwrap.json", "npm"),
    ("package-lock.json", "npm"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
)
AMBIGUOUS_MANAGER_ISSUES = frozenset(
    (
        "conflicting-package-managers",
        "invalid-package-manager-declaration",
        "unsupported-package-manager",
    ),
)


def collect_package_workspace_evidence(root: Path) -> PackageWorkspaceEvidence:
    """Return fixed-root advisory package-manager and workspace facts."""
    package_data, package_issues = _load_package_json(root)
    signals = [*_lockfile_signals(root)]
    issues = [*package_issues]
    if package_data is not None:
        declared_signals, declared_issues = _package_manager_signals(package_data)
        signals.extend(declared_signals)
        issues.extend(declared_issues)
    declarations: list[WorkspaceDeclaration] = []
    if package_data is not None:
        package_declarations, workspace_issues = _package_workspace_declarations(package_data)
        declarations.extend(package_declarations)
        issues.extend(workspace_issues)
    pnpm_declarations, pnpm_issues = _pnpm_workspace_declarations(root)
    agent_declarations, agent_issues = _agent_workspace_declarations(root)
    declarations.extend((*pnpm_declarations, *agent_declarations))
    issues.extend((*pnpm_issues, *agent_issues))
    issues.extend(_manager_conflict_issues(signals))
    ordered_signals = tuple(sorted(signals, key=_signal_key))
    ordered_declarations = tuple(sorted(declarations, key=_declaration_key))
    ordered_issues = tuple(sorted(issues, key=_issue_key))
    managers = frozenset(signal.manager for signal in ordered_signals)
    ambiguous = len(managers) > 1 or any(
        issue.kind in AMBIGUOUS_MANAGER_ISSUES for issue in ordered_issues
    )
    unambiguous_manager = next(iter(managers)) if len(managers) == 1 and not ambiguous else ""
    return PackageWorkspaceEvidence(
        manager_signals=ordered_signals,
        workspace_declarations=ordered_declarations,
        issues=ordered_issues,
        unambiguous_manager=unambiguous_manager,
        ambiguous=ambiguous,
    )


def _load_package_json(
    root: Path,
) -> tuple[Mapping[str, object] | None, tuple[PackageWorkspaceIssue, ...]]:
    path = root / "package.json"
    if not path.is_file():
        return None, ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError) as exc:
        return None, (_issue("malformed-package-json", "package.json", "", str(exc)),)
    if not isinstance(payload, dict):
        return None, (
            _issue(
                "malformed-package-json",
                "package.json",
                "",
                "package.json root must be an object.",
            ),
        )
    return cast(Mapping[str, object], payload), ()


def _package_manager_signals(
    data: Mapping[str, object],
) -> tuple[list[PackageManagerSignal], list[PackageWorkspaceIssue]]:
    signals: list[PackageManagerSignal] = []
    issues: list[PackageWorkspaceIssue] = []
    if "packageManager" in data:
        signal, issue = _top_level_manager_signal(data["packageManager"])
        if signal is not None:
            signals.append(signal)
        if issue is not None:
            issues.append(issue)
    dev_engines = data.get("devEngines")
    if isinstance(dev_engines, dict) and "packageManager" in dev_engines:
        signal, issue = _dev_engines_manager_signal(
            cast(Mapping[str, object], dev_engines)["packageManager"],
        )
        if signal is not None:
            signals.append(signal)
        if issue is not None:
            issues.append(issue)
    return signals, issues


def _package_workspace_declarations(
    data: Mapping[str, object],
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    if "workspaces" not in data:
        return [], []
    raw = data["workspaces"]
    field = "workspaces"
    if isinstance(raw, dict):
        workspace_data = cast(Mapping[str, object], raw)
        if "packages" not in workspace_data:
            return [], [_invalid_workspace_issue("package.json", field)]
        raw = workspace_data["packages"]
        field = "workspaces.packages"
    patterns, issues = _literal_patterns(raw, "package.json", field)
    if patterns is None:
        return [], issues
    return [WorkspaceDeclaration("package-json", "", "package.json", field, patterns)], issues


def _pnpm_workspace_declarations(
    root: Path,
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    path = root / "pnpm-workspace.yaml"
    if not path.is_file():
        return [], []
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, RecursionError) as exc:
        return [], [
            _issue("malformed-pnpm-workspace", path.name, "", str(exc)),
        ]
    if not isinstance(payload, dict):
        return [], [_invalid_workspace_issue(path.name, "packages")]
    data = cast(Mapping[str, object], payload)
    if "packages" not in data:
        return [], []
    patterns, issues = _literal_patterns(data["packages"], path.name, "packages")
    if patterns is None:
        return [], issues
    return [WorkspaceDeclaration("pnpm-workspace", "", path.name, "packages", patterns)], issues


def _agent_workspace_declarations(
    root: Path,
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return [], []
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [], [
            _issue("malformed-agent-maintainer-config", path.name, "", str(exc)),
        ]
    return _configured_agent_workspace_declarations(payload, path.name)


def _configured_agent_workspace_declarations(
    payload: Mapping[str, object],
    filename: str,
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        return [], []
    maintainer = cast(Mapping[str, object], tool).get("agent_maintainer")
    if not isinstance(maintainer, dict):
        return [], []
    maintainer_data = cast(Mapping[str, object], maintainer)
    if "workspaces" not in maintainer_data:
        return [], []
    workspaces = maintainer_data["workspaces"]
    if not isinstance(workspaces, dict):
        return [], [_invalid_workspace_issue(filename, "tool.agent_maintainer.workspaces")]
    declarations: list[WorkspaceDeclaration] = []
    issues: list[PackageWorkspaceIssue] = []
    for name, value in sorted(cast(Mapping[str, object], workspaces).items()):
        field = f"tool.agent_maintainer.workspaces.{name}"
        if not isinstance(value, dict):
            issues.append(_invalid_workspace_issue(filename, field))
            continue
        declarations.append(WorkspaceDeclaration("agent-maintainer", name, filename, field, ()))
    return declarations, issues


def _literal_patterns(
    value: object,
    path: str,
    field: str,
) -> tuple[tuple[str, ...] | None, list[PackageWorkspaceIssue]]:
    if not isinstance(value, list):
        return None, [_invalid_workspace_issue(path, field)]
    patterns = tuple(sorted(item for item in value if isinstance(item, str)))
    issues = [] if len(patterns) == len(value) else [_invalid_workspace_issue(path, field)]
    return patterns, issues


def _invalid_workspace_issue(path: str, field: str) -> PackageWorkspaceIssue:
    return _issue(
        "invalid-workspace-declaration",
        path,
        field,
        f"{path}#{field} must contain a string workspace pattern list or table.",
    )


def _top_level_manager_signal(
    value: object,
) -> tuple[PackageManagerSignal | None, PackageWorkspaceIssue | None]:
    field = "packageManager"
    if not isinstance(value, str):
        return None, _invalid_manager_issue(field, "packageManager must be a string.")
    name, separator, descriptor = value.partition("@")
    if not separator or not name or not descriptor:
        return None, _invalid_manager_issue(
            field,
            "packageManager must use a non-empty name@descriptor value.",
        )
    return _recognized_manager_signal(name, "package-manager-field", field, value)


def _dev_engines_manager_signal(
    value: object,
) -> tuple[PackageManagerSignal | None, PackageWorkspaceIssue | None]:
    field = "devEngines.packageManager"
    if not isinstance(value, dict):
        return None, _invalid_manager_issue(field, f"{field} must be an object.")
    manager = cast(Mapping[str, object], value)
    name = manager.get("name")
    version = manager.get("version")
    if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
        return None, _invalid_manager_issue(
            field,
            f"{field} requires non-empty string name and version fields.",
        )
    return _recognized_manager_signal(
        name,
        "corepack-dev-engines",
        field,
        f"{name}@{version}",
    )


def _recognized_manager_signal(
    name: str,
    kind: str,
    field: str,
    value: str,
) -> tuple[PackageManagerSignal | None, PackageWorkspaceIssue | None]:
    normalized = name.lower()
    if normalized not in SUPPORTED_MANAGERS:
        return None, _issue(
            "unsupported-package-manager",
            "package.json",
            field,
            f"Unsupported package manager declaration: {name}.",
        )
    return (
        PackageManagerSignal(
            manager=normalized,
            kind=kind,
            source_path="package.json",
            source_field=field,
            value=value,
        ),
        None,
    )


def _lockfile_signals(root: Path) -> tuple[PackageManagerSignal, ...]:
    return tuple(
        PackageManagerSignal(manager, "lockfile", filename, "", filename)
        for filename, manager in LOCKFILE_MANAGERS
        if (root / filename).is_file()
    )


def _manager_conflict_issues(
    signals: list[PackageManagerSignal],
) -> tuple[PackageWorkspaceIssue, ...]:
    managers = tuple(sorted({signal.manager for signal in signals}))
    if len(managers) <= 1:
        return ()
    return (
        _issue(
            "conflicting-package-managers",
            ".",
            "",
            f"Conflicting package-manager signals: {', '.join(managers)}.",
        ),
    )


def _invalid_manager_issue(field: str, message: str) -> PackageWorkspaceIssue:
    return _issue("invalid-package-manager-declaration", "package.json", field, message)


def _issue(kind: str, path: str, field: str, message: str) -> PackageWorkspaceIssue:
    return PackageWorkspaceIssue(kind, path, field, message)


def _signal_key(signal: PackageManagerSignal) -> tuple[str, str, str, str, str]:
    return (
        signal.manager,
        signal.kind,
        signal.source_path,
        signal.source_field,
        signal.value,
    )


def _issue_key(issue: PackageWorkspaceIssue) -> tuple[str, str, str, str]:
    return (issue.kind, issue.source_path, issue.source_field, issue.message)


def _declaration_key(
    declaration: WorkspaceDeclaration,
) -> tuple[str, str, str, str, tuple[str, ...]]:
    return (
        declaration.kind,
        declaration.name,
        declaration.source_path,
        declaration.source_field,
        declaration.patterns,
    )
