"""Tests advisory package-manager and workspace evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess.models import PackageManagerSignal
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


def test_keeps_typed_string_patterns_and_reports_invalid_entries(tmp_path: Path) -> None:
    write_json(
        tmp_path / "package.json",
        {"workspaces": ["apps/*", 7, None, {"unexpected": "value"}]},
    )
    (tmp_path / "pnpm-workspace.yaml").write_text(
        "packages:\n  - packages/*\n  - false\n",
        encoding=TEXT_ENCODING,
    )

    evidence = collect_package_workspace_evidence(tmp_path)

    assert [item.patterns for item in evidence.workspace_declarations] == [
        ("apps/*",),
        ("packages/*",),
    ]
    assert all(
        isinstance(pattern, str)
        for declaration in evidence.workspace_declarations
        for pattern in declaration.patterns
    )
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


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding=TEXT_ENCODING)
