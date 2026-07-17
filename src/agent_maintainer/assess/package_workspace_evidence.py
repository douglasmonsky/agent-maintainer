"""Advisory package-manager and workspace evidence collection."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

import yaml

from agent_maintainer.assess.models import (
    PackageManagerSignal,
    PackageWorkspaceEvidence,
    PackageWorkspaceIssue,
    WorkspaceDeclaration,
)
from agent_maintainer.core.structured_values import json_object

PACKAGE_JSON = "package.json"
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
    signals, manager_issues = _collect_manager_evidence(root, package_data)
    declarations, workspace_issues = _collect_workspace_evidence(root, package_data)
    issues = list(package_issues)
    issues.extend(manager_issues)
    issues.extend(workspace_issues)
    issues.extend(_manager_conflict_issues(signals))
    return _ordered_evidence(signals, declarations, issues)


def _collect_manager_evidence(
    root: Path,
    package_data: dict[str, object] | None,
) -> tuple[list[PackageManagerSignal], list[PackageWorkspaceIssue]]:
    signals = list(_lockfile_signals(root))
    issues: list[PackageWorkspaceIssue] = []
    if package_data is not None:
        declared_signals, declared_issues = _package_manager_signals(package_data)
        signals.extend(declared_signals)
        issues.extend(declared_issues)
    return signals, issues


def _collect_workspace_evidence(
    root: Path,
    package_data: dict[str, object] | None,
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    declarations: list[WorkspaceDeclaration] = []
    issues: list[PackageWorkspaceIssue] = []
    if package_data is not None:
        _extend_workspace_result(
            declarations,
            issues,
            _package_workspace_declarations(package_data),
        )
    _extend_workspace_result(declarations, issues, _pnpm_workspace_declarations(root))
    _extend_workspace_result(declarations, issues, _agent_workspace_declarations(root))
    return declarations, issues


def _extend_workspace_result(
    declarations: list[WorkspaceDeclaration],
    issues: list[PackageWorkspaceIssue],
    result: tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]],
) -> None:
    new_declarations, new_issues = result
    declarations.extend(new_declarations)
    issues.extend(new_issues)


def _ordered_evidence(
    signals: list[PackageManagerSignal],
    declarations: list[WorkspaceDeclaration],
    issues: list[PackageWorkspaceIssue],
) -> PackageWorkspaceEvidence:
    ordered_signals = tuple(sorted(signals))
    ordered_declarations = tuple(sorted(declarations))
    ordered_issues = tuple(sorted(issues))
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
) -> tuple[dict[str, object] | None, tuple[PackageWorkspaceIssue, ...]]:
    path = root / PACKAGE_JSON
    if not path.is_file():
        return None, ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, RecursionError) as exc:
        return None, (_issue("malformed-package-json", PACKAGE_JSON, "", str(exc)),)
    package_data = json_object(payload)
    if package_data is None:
        return None, (
            _issue(
                "malformed-package-json",
                PACKAGE_JSON,
                "",
                "package.json root must be an object.",
            ),
        )
    return package_data, ()


def _package_manager_signals(
    data: dict[str, object],
) -> tuple[list[PackageManagerSignal], list[PackageWorkspaceIssue]]:
    signals: list[PackageManagerSignal] = []
    issues: list[PackageWorkspaceIssue] = []
    if "packageManager" in data:
        signal, issue = _top_level_manager_signal(data.get("packageManager"))
        if signal is not None:
            signals.append(signal)
        if issue is not None:
            issues.append(issue)
    dev_engines = json_object(data.get("devEngines"))
    if dev_engines is not None and "packageManager" in dev_engines:
        signal, issue = _dev_engines_manager_signal(dev_engines.get("packageManager"))
        if signal is not None:
            signals.append(signal)
        if issue is not None:
            issues.append(issue)
    return signals, issues


def _package_workspace_declarations(
    data: dict[str, object],
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    if "workspaces" not in data:
        return [], []
    raw = data.get("workspaces")
    field = "workspaces"
    workspace_data = json_object(raw)
    if workspace_data is not None:
        if "packages" not in workspace_data:
            return [], [_invalid_workspace_issue(PACKAGE_JSON, field)]
        raw = workspace_data["packages"]
        field = "workspaces.packages"
    patterns, issues = _literal_patterns(raw, PACKAGE_JSON, field)
    if patterns is None:
        return [], issues
    return [WorkspaceDeclaration("package-json", "", PACKAGE_JSON, field, patterns)], issues


def _pnpm_workspace_declarations(
    root: Path,
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    data, issues = _load_pnpm_workspace(root)
    if data is None:
        return [], issues
    if "packages" not in data:
        return [], []
    patterns, pattern_issues = _literal_patterns(
        data.get("packages"),
        "pnpm-workspace.yaml",
        "packages",
    )
    if patterns is None:
        return [], pattern_issues
    return [
        WorkspaceDeclaration(
            "pnpm-workspace",
            "",
            "pnpm-workspace.yaml",
            "packages",
            patterns,
        ),
    ], pattern_issues


def _load_pnpm_workspace(
    root: Path,
) -> tuple[dict[str, object] | None, list[PackageWorkspaceIssue]]:
    path = root / "pnpm-workspace.yaml"
    if not path.is_file():
        return None, []
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, RecursionError) as exc:
        return None, [
            _issue("malformed-pnpm-workspace", path.name, "", str(exc)),
        ]
    data = json_object(payload)
    if data is None:
        return None, [_invalid_workspace_issue(path.name, "packages")]
    return data, []


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
    return _configured_agent_workspace_declarations(json_object(payload) or {}, path.name)


def _configured_agent_workspace_declarations(
    payload: dict[str, object],
    filename: str,
) -> tuple[list[WorkspaceDeclaration], list[PackageWorkspaceIssue]]:
    tool = json_object(payload.get("tool"))
    if tool is None:
        return [], []
    maintainer = json_object(tool.get("agent_maintainer"))
    if maintainer is None:
        return [], []
    if "workspaces" not in maintainer:
        return [], []
    workspaces = json_object(maintainer.get("workspaces"))
    if workspaces is None:
        return [], [_invalid_workspace_issue(filename, "tool.agent_maintainer.workspaces")]
    declarations: list[WorkspaceDeclaration] = []
    issues: list[PackageWorkspaceIssue] = []
    for name, value in sorted(workspaces.items()):
        field = f"tool.agent_maintainer.workspaces.{name}"
        if json_object(value) is None:
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
    items = cast(list[object], value)
    patterns = tuple(sorted(item for item in items if isinstance(item, str)))
    issues = [] if len(patterns) == len(items) else [_invalid_workspace_issue(path, field)]
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
        return None, _issue(
            "invalid-package-manager-declaration",
            PACKAGE_JSON,
            field,
            "packageManager must be a string.",
        )
    name, separator, descriptor = value.partition("@")
    if not separator or not name or not descriptor:
        return None, _issue(
            "invalid-package-manager-declaration",
            PACKAGE_JSON,
            field,
            "packageManager must use a non-empty name@descriptor value.",
        )
    return _recognized_manager_signal(name, "package-manager-field", field, value)


def _dev_engines_manager_signal(
    value: object,
) -> tuple[PackageManagerSignal | None, PackageWorkspaceIssue | None]:
    field = "devEngines.packageManager"
    manager = json_object(value)
    if manager is None:
        return None, _issue(
            "invalid-package-manager-declaration",
            PACKAGE_JSON,
            field,
            f"{field} must be an object.",
        )
    name = manager.get("name")
    version = manager.get("version")
    if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
        return None, _issue(
            "invalid-package-manager-declaration",
            PACKAGE_JSON,
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
            PACKAGE_JSON,
            field,
            f"Unsupported package manager declaration: {name}.",
        )
    return (
        PackageManagerSignal(
            manager=normalized,
            kind=kind,
            source_path=PACKAGE_JSON,
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
    manager_names = ", ".join(managers)
    return (
        _issue(
            "conflicting-package-managers",
            ".",
            "",
            f"Conflicting package-manager signals: {manager_names}.",
        ),
    )


def _issue(kind: str, path: str, field: str, message: str) -> PackageWorkspaceIssue:
    return PackageWorkspaceIssue(kind, path, field, message)
