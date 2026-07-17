# TypeScript Package And Workspace Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Phase 178 by reporting provenance-rich, advisory package-manager and workspace declarations without changing provider enablement, configuration, or command execution.

**Architecture:** A new assessment-owned detector reads a fixed set of root metadata files and returns frozen evidence dataclasses. `collect_evidence()` attaches those facts to `RepoEvidence`, and setup-advisor helpers render concise reasons and prompts; the TypeScript provider and executor remain unaware of detected evidence.

**Tech Stack:** Python 3.11+, frozen dataclasses, `json`, `tomllib`, existing PyYAML `safe_load`, pytest, DocSync, Markdown.

## Global Constraints

- Detection is advisory and declaration-only.
- Read only root `package.json`, recognized root lockfiles, root `pnpm-workspace.yaml`, and root `pyproject.toml`.
- Never expand workspace globs, scan nested packages for ownership, select a package manager, enable a provider, or generate a command.
- `TypeScriptProvider`, provider metadata, configuration coercion, catalogs, and executor code must not import package/workspace evidence.
- Existing explicit root and workspace commands must behave identically for missing, malformed, or contradictory evidence.
- Preserve file-and-field provenance and stable issue kinds in setup assessment JSON.
- TypeScript/React remains experimental; setup track and preset selection remain unchanged.
- Add no dependency, workflow, architecture-policy, or configuration-schema change.
- Use synthetic temporary-repository fixtures only.
- Use `.venv/bin` first on `PATH`; never bypass Git hooks.

---

## File Map

- Create `src/agent_maintainer/assess/package_workspace_evidence.py`: pure root metadata detector and ambiguity derivation.
- Modify `src/agent_maintainer/assess/models.py`: frozen public evidence dataclasses and `RepoEvidence.package_workspace`.
- Modify `src/agent_maintainer/assess/evidence.py`: attach the detector result without changing scan or script behavior.
- Create `tests/assess/test_package_workspace_evidence.py`: direct signal, workspace, malformed-input, conflict, and nesting tests.
- Modify `tests/assess/test_evidence.py`: collector integration and compatibility test.
- Modify `src/agent_maintainer/assess/setup_advisor.py`: pure evidence-to-text helpers.
- Modify `tests/assess/test_setup_advisor.py`: JSON, reason, prompt, ambiguity, and track-preservation tests.
- Modify `.docsync/trace.yml` and `tests/docsync/test_public_doc_trace.py`: trace the public setup-advisor claim to the new detector tests.
- Modify `docs/setup-advisor.md`, `docs/provider-status.md`, `docs/ROADMAP.md`, `docs/roadmap/typescript-react-parity-roadmap.md`, and `docs/roadmap/full-roadmap-blueprint.md`: document completed behavior and next work.
- Create `docs/roadmap/phases/phase-178-advisory-package-manager-workspace-detection.md`: completed phase record.
- Modify `tests/docs/test_first_touch_docs.py` and `tests/docs/test_roadmap_docs.py`: ratchet public wording and phase continuity.

---

### Task 1: Typed Package And Workspace Detector

**Files:**

- Create: `src/agent_maintainer/assess/package_workspace_evidence.py`
- Modify: `src/agent_maintainer/assess/models.py:3-43`
- Create: `tests/assess/test_package_workspace_evidence.py`

**Interfaces:**

- Consumes: resolved repository root `Path`.
- Produces: `collect_package_workspace_evidence(root: Path) -> PackageWorkspaceEvidence`.
- Produces: frozen `PackageManagerSignal`, `WorkspaceDeclaration`, `PackageWorkspaceIssue`, and `PackageWorkspaceEvidence` dataclasses.

- [ ] **Step 1: Write failing package-manager signal tests**

Create `tests/assess/test_package_workspace_evidence.py` with the initial direct tests:

```python
"""Tests advisory package-manager and workspace evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess.package_workspace_evidence import (
    collect_package_workspace_evidence,
)

TEXT_ENCODING = "utf-8"


# docsync:evidence.start evidence.typescript.package_workspace_detection_tests
@pytest.mark.parametrize(
    ("filename", "manager"),
    (
        ("package-lock.json", "npm"),
        ("npm-shrinkwrap.json", "npm"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
    ),
)
def test_detects_recognized_root_lockfiles(
    tmp_path: Path,
    filename: str,
    manager: str,
) -> None:
    (tmp_path / filename).write_text("", encoding=TEXT_ENCODING)

    evidence = collect_package_workspace_evidence(tmp_path)

    assert evidence.manager_signals == (
        PackageManagerSignal(
            manager=manager,
            kind="lockfile",
            source_path=filename,
            source_field="",
            value=filename,
        ),
    )
    assert evidence.unambiguous_manager == manager
    assert evidence.ambiguous is False


def test_correlates_package_manager_and_corepack_declarations(tmp_path: Path) -> None:
    write_json(
        tmp_path / "package.json",
        {
            "packageManager": "pnpm@9.15.0",
            "devEngines": {
                "packageManager": {"name": "pnpm", "version": "9.15.0"},
            },
        },
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding=TEXT_ENCODING)

    evidence = collect_package_workspace_evidence(tmp_path)

    assert [signal.manager for signal in evidence.manager_signals] == ["pnpm"] * 3
    assert [signal.kind for signal in evidence.manager_signals] == [
        "corepack-dev-engines",
        "lockfile",
        "package-manager-field",
    ]
    assert evidence.unambiguous_manager == "pnpm"
    assert evidence.issues == ()


def test_reports_unsupported_invalid_and_conflicting_managers(tmp_path: Path) -> None:
    write_json(
        tmp_path / "package.json",
        {
            "packageManager": "deno@2.0.0",
            "devEngines": {"packageManager": {"name": "pnpm", "version": ""}},
        },
    )
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding=TEXT_ENCODING)
    (tmp_path / "yarn.lock").write_text("", encoding=TEXT_ENCODING)

    evidence = collect_package_workspace_evidence(tmp_path)

    assert {issue.kind for issue in evidence.issues} == {
        "conflicting-package-managers",
        "invalid-package-manager-declaration",
        "unsupported-package-manager",
    }
    assert evidence.unambiguous_manager == ""
    assert evidence.ambiguous is True


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding=TEXT_ENCODING)
```

Add `PackageManagerSignal` to the import once the model exists in Step 3. Keep the DocSync end marker for Task 2, after the remaining detector tests.

- [ ] **Step 2: Run the direct tests and verify RED**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py
```

Expected: collection fails because `agent_maintainer.assess.package_workspace_evidence` and the evidence dataclasses do not exist.

- [ ] **Step 3: Add the frozen evidence models**

Change the dataclass import in `src/agent_maintainer/assess/models.py` and add these definitions immediately before `RepoEvidence`:

```python
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class PackageManagerSignal:
    """One provenance-bearing package-manager observation."""

    manager: str
    kind: str
    source_path: str
    source_field: str
    value: str


@dataclass(frozen=True)
class WorkspaceDeclaration:
    """One literal workspace declaration without inferred ownership."""

    kind: str
    name: str
    source_path: str
    source_field: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class PackageWorkspaceIssue:
    """One advisory package or workspace evidence issue."""

    kind: str
    source_path: str
    source_field: str
    message: str


@dataclass(frozen=True)
class PackageWorkspaceEvidence:
    """Advisory root package-manager and workspace evidence."""

    manager_signals: tuple[PackageManagerSignal, ...] = ()
    workspace_declarations: tuple[WorkspaceDeclaration, ...] = ()
    issues: tuple[PackageWorkspaceIssue, ...] = ()
    unambiguous_manager: str = ""
    ambiguous: bool = False
```

Append the compatible default to `RepoEvidence` after `java_module_paths`:

```python
    package_workspace: PackageWorkspaceEvidence = field(
        default_factory=PackageWorkspaceEvidence,
    )
```

- [ ] **Step 4: Implement only package-manager detection**

Create `src/agent_maintainer/assess/package_workspace_evidence.py` with the package signal boundary:

```python
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
    issues.extend(_manager_conflict_issues(signals))
    ordered_signals = tuple(sorted(signals, key=_signal_key))
    ordered_issues = tuple(sorted(issues, key=_issue_key))
    managers = frozenset(signal.manager for signal in ordered_signals)
    ambiguous = len(managers) > 1 or any(
        issue.kind in AMBIGUOUS_MANAGER_ISSUES for issue in ordered_issues
    )
    unambiguous_manager = next(iter(managers)) if len(managers) == 1 and not ambiguous else ""
    return PackageWorkspaceEvidence(
        manager_signals=ordered_signals,
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
```

The `tomllib`, `yaml`, and `WorkspaceDeclaration` imports are intentionally present for Task 2, which completes this module before the first commit.

- [ ] **Step 5: Import the model in the test and verify GREEN**

Add this import to `tests/assess/test_package_workspace_evidence.py`:

```python
from agent_maintainer.assess.models import PackageManagerSignal
```

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py
```

Expected: all initial package-manager tests pass.

---

#### Workspace declarations and collector integration

**Files:**

- Modify: `src/agent_maintainer/assess/package_workspace_evidence.py`
- Modify: `src/agent_maintainer/assess/evidence.py:45-118`
- Modify: `tests/assess/test_package_workspace_evidence.py`
- Modify: `tests/assess/test_evidence.py:55-96`

**Interfaces:**

- Consumes: the package-manager detector and evidence dataclasses defined above.
- Produces: literal `WorkspaceDeclaration` facts from package JSON, pnpm YAML, and Agent Maintainer TOML.
- Produces: `RepoEvidence.package_workspace` populated by `collect_evidence()`.

- [ ] **Step 1: Add failing workspace and malformed-input tests**

Append these tests before the DocSync end marker in `tests/assess/test_package_workspace_evidence.py`:

```python
def test_reports_literal_workspace_declarations_with_provenance(tmp_path: Path) -> None:
    write_json(
        tmp_path / "package.json",
        {"workspaces": {"packages": ["apps/*", "packages/*"]}},
    )
    (tmp_path / "pnpm-workspace.yaml").write_text(
        "packages:\n  - packages/*\n  - tools/*\n",
        encoding=TEXT_ENCODING,
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.agent_maintainer.workspaces.web]
source_roots = ["apps/web/src"]

[tool.agent_maintainer.workspaces.api]
source_roots = ["apps/api/src"]
""".strip(),
        encoding=TEXT_ENCODING,
    )

    evidence = collect_package_workspace_evidence(tmp_path)

    assert [item.kind for item in evidence.workspace_declarations] == [
        "agent-maintainer",
        "agent-maintainer",
        "package-json",
        "pnpm-workspace",
    ]
    assert evidence.workspace_declarations[0].name == "api"
    assert evidence.workspace_declarations[2].patterns == ("apps/*", "packages/*")
    assert evidence.workspace_declarations[3].patterns == ("packages/*", "tools/*")


def test_keeps_valid_patterns_and_reports_invalid_entries(tmp_path: Path) -> None:
    write_json(tmp_path / "package.json", {"workspaces": ["apps/*", 7]})
    (tmp_path / "pnpm-workspace.yaml").write_text(
        "packages:\n  - packages/*\n  - false\n",
        encoding=TEXT_ENCODING,
    )

    evidence = collect_package_workspace_evidence(tmp_path)

    assert [item.patterns for item in evidence.workspace_declarations] == [
        ("apps/*",),
        ("packages/*",),
    ]
    assert [issue.kind for issue in evidence.issues] == [
        "invalid-workspace-declaration",
        "invalid-workspace-declaration",
    ]


@pytest.mark.parametrize(
    ("filename", "content", "issue_kind"),
    (
        ("package.json", "{", "malformed-package-json"),
        ("pnpm-workspace.yaml", "packages: [", "malformed-pnpm-workspace"),
        ("pyproject.toml", "[tool", "malformed-agent-maintainer-config"),
    ),
)
def test_reports_malformed_root_metadata(
    tmp_path: Path,
    filename: str,
    content: str,
    issue_kind: str,
) -> None:
    (tmp_path / filename).write_text(content, encoding=TEXT_ENCODING)

    evidence = collect_package_workspace_evidence(tmp_path)

    assert issue_kind in {issue.kind for issue in evidence.issues}


def test_does_not_expand_or_scan_nested_workspace_packages(tmp_path: Path) -> None:
    write_json(tmp_path / "package.json", {"workspaces": ["packages/*"]})
    nested = tmp_path / "packages" / "web"
    nested.mkdir(parents=True)
    write_json(nested / "package.json", {"packageManager": "yarn@4.6.0"})

    evidence = collect_package_workspace_evidence(tmp_path)

    assert evidence.manager_signals == ()
    assert evidence.workspace_declarations[0].patterns == ("packages/*",)


# docsync:evidence.end evidence.typescript.package_workspace_detection_tests
```

- [ ] **Step 2: Run the workspace tests and verify RED**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py
```

Expected: workspace declarations are empty and malformed pnpm/TOML issues are absent.

- [ ] **Step 3: Add workspace collection to the detector**

In `collect_package_workspace_evidence()`, collect workspace declarations and their issues before ordering:

```python
    declarations: list[WorkspaceDeclaration] = []
    if package_data is not None:
        package_declarations, workspace_issues = _package_workspace_declarations(package_data)
        declarations.extend(package_declarations)
        issues.extend(workspace_issues)
    pnpm_declarations, pnpm_issues = _pnpm_workspace_declarations(root)
    agent_declarations, agent_issues = _agent_workspace_declarations(root)
    declarations.extend((*pnpm_declarations, *agent_declarations))
    issues.extend((*pnpm_issues, *agent_issues))
```

Order declarations and pass them into the aggregate:

```python
    ordered_declarations = tuple(sorted(declarations, key=_declaration_key))
    return PackageWorkspaceEvidence(
        manager_signals=ordered_signals,
        workspace_declarations=ordered_declarations,
        issues=ordered_issues,
        unambiguous_manager=unambiguous_manager,
        ambiguous=ambiguous,
    )
```

Add the complete workspace helpers:

```python
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
        return [], [_invalid_workspace_issue(path.name, "tool.agent_maintainer.workspaces")]
    declarations: list[WorkspaceDeclaration] = []
    issues: list[PackageWorkspaceIssue] = []
    for name, value in sorted(cast(Mapping[str, object], workspaces).items()):
        field = f"tool.agent_maintainer.workspaces.{name}"
        if not isinstance(value, dict):
            issues.append(_invalid_workspace_issue(path.name, field))
            continue
        declarations.append(WorkspaceDeclaration("agent-maintainer", name, path.name, field, ()))
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
```

- [ ] **Step 4: Verify the complete detector is GREEN**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py
```

Expected: all direct detector tests pass with no warnings.

- [ ] **Step 5: Add a failing collector integration test**

Append to `tests/assess/test_evidence.py`:

```python
def test_collect_evidence_includes_package_workspace_facts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"packageManager": "pnpm@9.15.0", "workspaces": ["packages/*"]}),
        encoding=TEXT_ENCODING,
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding=TEXT_ENCODING)

    evidence = collect_evidence(tmp_path)

    assert evidence.package_workspace.unambiguous_manager == "pnpm"
    assert evidence.package_workspace.workspace_declarations[0].patterns == ("packages/*",)
    assert evidence.package_scripts == ()
```

- [ ] **Step 6: Run the collector test and verify RED**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_evidence.py::test_collect_evidence_includes_package_workspace_facts
```

Expected: `RepoEvidence.package_workspace` remains the empty default.

- [ ] **Step 7: Wire the detector into `collect_evidence()`**

Add the import:

```python
from agent_maintainer.assess.package_workspace_evidence import (
    collect_package_workspace_evidence,
)
```

Compute once after resolving the root:

```python
    package_workspace = collect_package_workspace_evidence(root)
```

Pass it into the `RepoEvidence` constructor after `java_module_paths`:

```python
        package_workspace=package_workspace,
```

- [ ] **Step 8: Run focused GREEN and static checks**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py tests/assess/test_evidence.py
PATH="$PWD/.venv/bin:$PATH" .venv/bin/ruff check src/agent_maintainer/assess/package_workspace_evidence.py src/agent_maintainer/assess/models.py src/agent_maintainer/assess/evidence.py tests/assess/test_package_workspace_evidence.py tests/assess/test_evidence.py
PATH="$PWD/.venv/bin:$PATH" .venv/bin/pyright src/agent_maintainer/assess/package_workspace_evidence.py src/agent_maintainer/assess/models.py src/agent_maintainer/assess/evidence.py
```

Expected: tests pass; Ruff and Pyright report no errors. If formatting differs, run Ruff format on only the touched Python files and rerun the same checks.

- [ ] **Step 9: Commit the typed detector slice**

```bash
git add -- src/agent_maintainer/assess/package_workspace_evidence.py src/agent_maintainer/assess/models.py src/agent_maintainer/assess/evidence.py tests/assess/test_package_workspace_evidence.py tests/assess/test_evidence.py
git commit -m "feat: detect TypeScript package workspace evidence"
```

---

### Task 2: Setup-Advisor Rendering And Safety Boundary

**Files:**

- Modify: `src/agent_maintainer/assess/setup_advisor.py:94-121,206-243`
- Modify: `tests/assess/test_setup_advisor.py:47-181`
- Verify unchanged: `src/agent_maintainer/ecosystems/typescript/provider.py`
- Verify unchanged: `tests/ecosystems/test_typescript_provider.py`
- Verify unchanged: `tests/catalogs/test_typescript_catalog.py`

**Interfaces:**

- Consumes: `RepoEvidence.package_workspace` from Task 1.
- Produces: `_package_workspace_reasons(evidence: RepoEvidence) -> tuple[str, ...]`.
- Produces: `_package_workspace_prompts(evidence: RepoEvidence) -> tuple[str, ...]`.
- Preserves: existing `SetupAdvisorReport.track`, `preset`, optional gate logic, and explicit provider commands.

- [ ] **Step 1: Write failing setup-advisor behavior tests**

Add these tests inside the existing `evidence.setup_advisor.recommendation_tests` DocSync region in `tests/assess/test_setup_advisor.py`:

```python
def test_setup_advisor_explains_corroborated_package_workspace_evidence(
    tmp_path: Path,
) -> None:
    write_package_script_commands(
        tmp_path,
        {
            "lint": "eslint .",
            "typecheck": "tsc --noEmit",
            "test": "vitest run",
        },
        package_manager="pnpm@9.15.0",
        workspaces=("packages/*",),
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "inspect"
    assert report.preset == "manual-review"
    assert any("advisory package-manager evidence for `pnpm`" in reason for reason in report.reasons)
    assert any("workspace declaration" in reason and "unexpanded" in reason for reason in report.reasons)
    assert any("explicit root or workspace commands" in prompt for prompt in report.agent_prompts)


def test_setup_advisor_keeps_conflicting_manager_evidence_advisory(tmp_path: Path) -> None:
    write_package_script_commands(
        tmp_path,
        {"test": "vitest run"},
        package_manager="pnpm@9.15.0",
    )
    (tmp_path / "yarn.lock").write_text("", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "inspect"
    assert report.evidence.package_workspace.ambiguous is True
    assert any("no package manager was selected" in reason for reason in report.reasons)
    assert any("Resolve package-manager evidence conflicts" in prompt for prompt in report.agent_prompts)
    assert {gate.name for gate in report.optional_gates} >= {"typescript-provider"}
```

Extend `write_package_script_commands()` without changing existing callers:

```python
def write_package_script_commands(
    root: Path,
    scripts: dict[str, str],
    *,
    package_manager: str = "",
    workspaces: tuple[str, ...] = (),
) -> None:
    """Write root package metadata used by setup-advisor tests."""
    payload: dict[str, object] = {"scripts": scripts}
    if package_manager:
        payload["packageManager"] = package_manager
    if workspaces:
        payload["workspaces"] = list(workspaces)
    (root / "package.json").write_text(json.dumps(payload), encoding=TEXT_ENCODING)
```

- [ ] **Step 2: Run the setup-advisor tests and verify RED**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_setup_advisor.py -k "package_workspace or conflicting_manager"
```

Expected: facts exist, but reasons and prompts do not yet mention them.

- [ ] **Step 3: Add pure reason rendering**

Extend `_reasons()` immediately after the three base reasons:

```python
    reasons.extend(_package_workspace_reasons(evidence))
```

Add these helpers near the other setup-advisor helpers:

```python
def _package_workspace_reasons(evidence: RepoEvidence) -> tuple[str, ...]:
    """Return concise advisory package-manager and workspace reasons."""
    facts = evidence.package_workspace
    reasons: list[str] = []
    if facts.unambiguous_manager:
        sources = ", ".join(
            _evidence_source(signal.source_path, signal.source_field)
            for signal in facts.manager_signals
        )
        reasons.append(
            f"Observed advisory package-manager evidence for `{facts.unambiguous_manager}` "
            f"from {sources}.",
        )
    elif facts.manager_signals:
        managers = ", ".join(sorted({signal.manager for signal in facts.manager_signals}))
        reasons.append(
            f"Observed ambiguous advisory package-manager evidence for {managers}; "
            "no package manager was selected.",
        )
    if facts.workspace_declarations:
        sources = ", ".join(
            _evidence_source(item.source_path, item.source_field)
            for item in facts.workspace_declarations
        )
        reasons.append(
            f"Observed {len(facts.workspace_declarations)} workspace declaration(s) from "
            f"{sources}; patterns remain advisory and unexpanded.",
        )
    if facts.issues:
        kinds = ", ".join(sorted({issue.kind for issue in facts.issues}))
        reasons.append(
            f"Package/workspace evidence reported advisory issue(s): {kinds}.",
        )
    return tuple(reasons)


def _evidence_source(path: str, field: str) -> str:
    """Return one compact file-and-field provenance label."""
    return f"`{path}#{field}`" if field else f"`{path}`"
```

- [ ] **Step 4: Add prompts on both inspect and supported paths**

Refactor the start of `_agent_prompts()` so the inspect branch appends package/workspace prompts:

```python
    if not _has_supported_surface(evidence):
        prompts = (
            "Identify the repo language, package manager, test command, and CI command.",
            "Confirm Agent Maintainer is appropriate before writing starter files.",
            "Run only a dry-run initializer until a supported surface is confirmed.",
        )
        return (*prompts, *_package_workspace_prompts(evidence))
```

Change the final return for supported repositories:

```python
    return (*prompts, *_package_workspace_prompts(evidence))
```

Add the prompt helper:

```python
def _package_workspace_prompts(evidence: RepoEvidence) -> tuple[str, ...]:
    """Return review prompts without inferring commands or ownership."""
    facts = evidence.package_workspace
    prompts: list[str] = []
    if facts.ambiguous:
        prompts.append(
            "Resolve package-manager evidence conflicts before choosing reviewed setup commands.",
        )
    if facts.manager_signals or facts.workspace_declarations:
        prompts.append(
            "Review detected declarations, then map existing scripts to explicit root or "
            "workspace commands; do not infer a package manager or package ownership.",
        )
    return tuple(prompts)
```

- [ ] **Step 5: Extend the stable JSON CLI assertion**

In `test_setup_advisor_json_cli()`, add:

```python
    assert payload["evidence"]["package_workspace"] == {
        "manager_signals": [],
        "workspace_declarations": [],
        "issues": [],
        "unambiguous_manager": "",
        "ambiguous": False,
    }
```

- [ ] **Step 6: Run setup and execution-boundary GREEN tests**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_setup_advisor.py tests/doctor/test_typescript_doctor.py tests/ecosystems/test_typescript_provider.py tests/catalogs/test_typescript_catalog.py
```

Expected: all tests pass. Confirm `git diff --name-only` does not list the TypeScript provider, catalogs, configuration modules, or executor modules.

- [ ] **Step 7: Run focused style and type checks**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" .venv/bin/ruff check src/agent_maintainer/assess/setup_advisor.py tests/assess/test_setup_advisor.py
PATH="$PWD/.venv/bin:$PATH" .venv/bin/pyright src/agent_maintainer/assess/setup_advisor.py
```

Expected: no errors. Format only these touched Python files if Ruff reports formatting drift, then rerun the focused tests.

- [ ] **Step 8: Commit the setup-advisor slice**

```bash
git add -- src/agent_maintainer/assess/setup_advisor.py tests/assess/test_setup_advisor.py
git commit -m "feat: explain TypeScript package workspace evidence"
```

---

### Task 3: Public Contract, DocSync, And Phase 178 Completion

**Files:**

- Modify: `.docsync/trace.yml:990-1000,1488-1496`
- Modify: `tests/docsync/test_public_doc_trace.py:50-75`
- Modify: `docs/setup-advisor.md:68-105`
- Modify: `docs/provider-status.md:15-34`
- Modify: `docs/ROADMAP.md:128-135`
- Modify: `docs/roadmap/typescript-react-parity-roadmap.md:20-92`
- Modify: `docs/roadmap/full-roadmap-blueprint.md:164-166`
- Create: `docs/roadmap/phases/phase-178-advisory-package-manager-workspace-detection.md`
- Modify: `tests/docs/test_first_touch_docs.py:162-187`
- Modify: `tests/docs/test_roadmap_docs.py:12-135`

**Interfaces:**

- Consumes: Tasks 1-2 behavior and the `evidence.typescript.package_workspace_detection_tests` marker.
- Produces: traced public documentation that describes advisory evidence and preserves explicit command ownership.
- Produces: completed Phase 178 record and identifies Knip facts as the next unnumbered slice.

- [ ] **Step 1: Write failing documentation ratchets**

In `tests/docs/test_first_touch_docs.py`, replace the future Phase 178 provider-status assertions with completed behavior and extend the setup-advisor test:

```python
def test_provider_status_tracks_typescript_package_workspace_evidence() -> None:
    """Provider status records completed advisory detection and the next parity slice."""
    text = Path("docs/provider-status.md").read_text(encoding="utf-8")
    for expected in (
        "Phase 178 package-manager and workspace evidence is advisory only.",
        "preserves file-and-field provenance",
        "never selects a manager",
        "expands workspace globs",
        "creates a command",
        "Knip unused-code and dependency facts",
        "next parity slice",
    ):
        assert expected in text


def test_setup_advisor_docs_explain_package_workspace_evidence() -> None:
    """Setup advisor docs explain facts, ambiguity, and explicit ownership."""
    text = Path("docs/setup-advisor.md").read_text(encoding="utf-8")
    for expected in (
        "`packageManager` and `devEngines.packageManager`",
        "`package-lock.json`",
        "`npm-shrinkwrap.json`",
        "`pnpm-lock.yaml`",
        "`yarn.lock`",
        "`bun.lock`",
        "`bun.lockb`",
        "Workspace patterns remain literal and unexpanded.",
        "Detected evidence never becomes a subprocess argument.",
    ):
        assert expected in text
```

In `tests/docs/test_roadmap_docs.py`, add the Phase 178 path constant and assertions:

```python
TYPESCRIPT_PACKAGE_WORKSPACE_PHASE = (
    PHASES_DIR / "phase-178-advisory-package-manager-workspace-detection.md"
)


def test_typescript_package_workspace_phase_is_complete_and_advisory() -> None:
    phase = TYPESCRIPT_PACKAGE_WORKSPACE_PHASE.read_text(encoding="utf-8")
    assert phase.startswith("# Phase 178: Advisory Package-Manager And Workspace Detection")
    assert "Status: complete" in phase
    assert "No inferred command execution" in phase
    assert "Knip unused-code and dependency facts" in phase
```

Update the parity sequence assertions to require:

```python
        "Phase 178: advisory package-manager and workspace detection is complete.",
        "Knip unused-code and dependency facts",
```

- [ ] **Step 2: Run documentation tests and verify RED**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py
```

Expected: missing completed Phase 178 wording and phase file failures.

- [ ] **Step 3: Document setup-advisor behavior**

Add this subsection after the existing TypeScript root/workspace command guidance in `docs/setup-advisor.md`:

```markdown
### Advisory package-manager and workspace evidence

Setup assessment JSON reports recognized root `packageManager` and
`devEngines.packageManager` declarations plus `package-lock.json`,
`npm-shrinkwrap.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, and `bun.lockb`
signals. It also reports root `package.json` workspaces, pnpm workspace patterns,
and explicit `[tool.agent_maintainer.workspaces.<name>]` tables with
file-and-field provenance.

Agreement is corroborating evidence; conflicting, unsupported, malformed, and
invalid declarations remain advisory issues. Workspace patterns remain literal
and unexpanded. Nested packages are not scanned to infer ownership. Detected
evidence never becomes a subprocess argument, enables a provider, or replaces
the explicit root and workspace command arrays shown above.
```

- [ ] **Step 4: Update provider status and both roadmaps**

In `docs/provider-status.md`, move package-manager/workspace detection from the missing column into the implemented TypeScript description and add this exact status paragraph:

```markdown
Phase 178 package-manager and workspace evidence is advisory only. The setup
assessment JSON preserves file-and-field provenance for recognized declarations,
lockfiles, and workspace manifests, but never selects a manager, expands
workspace globs, or creates a command. Knip unused-code and dependency facts are
the next parity slice; TypeScript/JavaScript remains experimental.
```

In `docs/ROADMAP.md`, mark Phase 178 complete without changing the file's compact structure:

```markdown
- [x] Phase 178: Advisory Package-Manager And Workspace Detection
```

In `docs/roadmap/typescript-react-parity-roadmap.md`:

- move advisory package-manager/workspace detection into “Already landed”;
- remove it from “Still missing”;
- make the first sequence item `Phase 178: advisory package-manager and workspace detection is complete.`;
- retain `Knip unused-code and dependency facts` as the next item; and
- rewrite the Phase 178 boundary section in past tense while preserving the no-command rule.

Append this row to `docs/roadmap/full-roadmap-blueprint.md`:

```markdown
| 178 | [Advisory Package-Manager And Workspace Detection](phases/phase-178-advisory-package-manager-workspace-detection.md) |
```

- [ ] **Step 5: Add the completed Phase 178 record**

Create `docs/roadmap/phases/phase-178-advisory-package-manager-workspace-detection.md`:

````markdown
# Phase 178: Advisory Package-Manager And Workspace Detection

Status: complete

## Goal

Report provenance-rich root package-manager and workspace declarations for
TypeScript/JavaScript setup assessment without inferring commands or package
ownership.

## Delivered

- Typed npm, pnpm, Yarn, and Bun declaration and lockfile signals.
- Literal package, pnpm, and explicit Agent Maintainer workspace declarations.
- Stable advisory issues for malformed, unsupported, invalid, and conflicting
  evidence.
- Setup-advisor reasons and prompts that preserve explicit command ownership.
- JSON evidence with file-and-field provenance.

## Safety Boundary

- No inferred command execution, provider enablement, or configuration mutation.
- No workspace glob expansion or nested package ownership inference.
- No package-manager selection when evidence agrees or conflicts.
- TypeScript/JavaScript remains experimental and advisory.

## Next Slice

Knip unused-code and dependency facts, with stable JSON parsing and external
repository evidence, are the next TypeScript/React parity slice.

## Verification

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py tests/assess/test_evidence.py tests/assess/test_setup_advisor.py tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py
.venv/bin/python -m docsync check
just v
```
````

- [ ] **Step 6: Trace the new public claim evidence**

In `.docsync/trace.yml`, extend `claim.docs.setup_advisor_recommendations.text` to mention provenance-rich package/workspace evidence and add:

```yaml
      - evidence.typescript.package_workspace_detection_tests
```

Add the evidence object near the existing setup-advisor evidence:

```yaml
  evidence.typescript.package_workspace_detection_tests:
    type: test
    description: Package and workspace detector tests cover npm, pnpm, Yarn, and Bun signals, Corepack declarations, literal workspace manifests, provenance, malformed metadata, conflicts, and nested-package non-inference.
    anchors:
      - path: tests/assess/test_package_workspace_evidence.py
        mode: explicit_region
```

Add `"evidence.typescript.package_workspace_detection_tests"` to the expected test-evidence identifiers in `tests/docsync/test_public_doc_trace.py`.

- [ ] **Step 7: Run documentation and DocSync GREEN checks**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m docsync check
node node_modules/.bin/markdownlint-cli2 docs/setup-advisor.md docs/provider-status.md docs/ROADMAP.md docs/roadmap/typescript-react-parity-roadmap.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/phases/phase-178-advisory-package-manager-workspace-detection.md docs/superpowers/specs/2026-07-17-typescript-package-workspace-evidence-design.md docs/superpowers/plans/2026-07-17-typescript-package-workspace-evidence.md
```

Expected: documentation tests, DocSync, and Markdown lint pass. Keep `docs/ROADMAP.md` within its compact line-count ratchet.

- [ ] **Step 8: Run the complete focused behavior suite**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src .venv/bin/pytest -q tests/assess/test_package_workspace_evidence.py tests/assess/test_evidence.py tests/assess/test_setup_advisor.py tests/doctor/test_typescript_doctor.py tests/ecosystems/test_typescript_provider.py tests/catalogs/test_typescript_catalog.py tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py tests/docsync/test_public_doc_trace.py
git diff --check
```

Expected: all focused tests pass and the diff has no whitespace errors.

- [ ] **Step 9: Commit the documentation slice**

```bash
git add -- .docsync/trace.yml tests/docsync/test_public_doc_trace.py docs/setup-advisor.md docs/provider-status.md docs/ROADMAP.md docs/roadmap/typescript-react-parity-roadmap.md docs/roadmap/full-roadmap-blueprint.md docs/roadmap/phases/phase-178-advisory-package-manager-workspace-detection.md tests/docs/test_first_touch_docs.py tests/docs/test_roadmap_docs.py
git commit -m "docs: complete TypeScript package workspace evidence phase"
```

---

## Final Verification And Publication

- [ ] **Step 1: Review status, scope, and safety boundary**

Run:

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
git diff --check origin/main...HEAD
git log --oneline origin/main..HEAD
```

Expected: only the specification, plan, assessment models/detector/collector/advisor, focused tests, DocSync trace, and TypeScript documentation are changed. Provider, catalog, executor, configuration, dependency, and workflow files are absent.

- [ ] **Step 2: Run one fresh full repository verifier**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1 just v
```

Expected: `PASS` with a fresh full-profile run ID. Existing structural warnings may remain, but no new failure is acceptable.

- [ ] **Step 3: Request final code review**

Generate a review package for `origin/main...HEAD` and request one comprehensive correctness/safety review. Resolve Critical and Important findings before publication; rerun focused tests after any change.

- [ ] **Step 4: Publish and merge through normal CI**

Push `codex/typescript-package-workspace-evidence`, create a ready pull request titled `feat: add TypeScript package workspace evidence`, watch the exact PR with `just wp <pr-number>`, and merge with a normal merge commit only after every required hosted check passes. Preserve the remote branch and do not rewrite history.
