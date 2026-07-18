"""Provider-neutral affected-unit resolution tests."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.assess.models import (
    PackageWorkspaceEvidence,
    WorkspaceDeclaration,
)
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.git_changes import GitPathChange
from agent_maintainer.ecosystems.models import (
    ChangeKind,
    FileChangeClassification,
    FileRole,
)
from agent_maintainer.verification_plan.units import (
    UnitResolutionInputs,
    resolve_affected_units,
)


def test_python_units_use_longest_segment_prefix(tmp_path: Path) -> None:
    config = MaintainerConfig(package_paths=("src/app", "src/application"))
    changes = (
        GitPathChange("src/app/api.py", "modified"),
        GitPathChange("src/application/main.py", "modified"),
    )

    units, advisories = resolve_affected_units(
        tmp_path,
        changes=changes,
        inputs=UnitResolutionInputs(
            config=config,
            classifications=(
                _classification("src/app/api.py", "python"),
                _classification("src/application/main.py", "python"),
            ),
            package_workspace=PackageWorkspaceEvidence(),
            java_module_paths=(),
        ),
    )

    assert [(unit.root, unit.changed_paths) for unit in units] == [
        ("src/app", ("src/app/api.py",)),
        ("src/application", ("src/application/main.py",)),
    ]
    assert advisories == ()


def test_typescript_workspace_requires_manifest_and_prefers_nested_root(
    tmp_path: Path,
) -> None:
    _write_package(tmp_path / "packages/web/package.json", "@demo/web")
    _write_package(tmp_path / "packages/web/admin/package.json", "@demo/admin")
    (tmp_path / "packages/missing").mkdir(parents=True)
    evidence = PackageWorkspaceEvidence(
        workspace_declarations=(
            WorkspaceDeclaration(
                kind="package-json",
                name="workspaces",
                source_path="package.json",
                source_field="workspaces",
                patterns=("packages/*", "packages/web/*"),
            ),
        ),
    )
    changes = (
        GitPathChange("packages/web/src/app.ts", "modified"),
        GitPathChange("packages/web/admin/src/panel.ts", "modified"),
        GitPathChange("packages/missing/src/ghost.ts", "modified"),
    )

    units, advisories = resolve_affected_units(
        tmp_path,
        changes=changes,
        inputs=UnitResolutionInputs(
            config=MaintainerConfig(),
            classifications=tuple(
                _classification(path, "typescript")
                for path in (
                    "packages/web/src/app.ts",
                    "packages/web/admin/src/panel.ts",
                    "packages/missing/src/ghost.ts",
                )
            ),
            package_workspace=evidence,
            java_module_paths=(),
        ),
    )

    assert [(unit.kind, unit.name, unit.root) for unit in units] == [
        ("repository", "repository", "."),
        ("typescript-workspace", "@demo/web", "packages/web"),
        ("typescript-workspace", "@demo/admin", "packages/web/admin"),
    ]
    assert units[0].changed_paths == ("packages/missing/src/ghost.ts",)
    assert any("packages/missing" in advisory for advisory in advisories)


def test_java_module_and_unclassified_paths_use_safe_units(tmp_path: Path) -> None:
    changes = (
        GitPathChange("services/api/src/main/java/App.java", "modified"),
        GitPathChange("README.md", "modified"),
    )

    units, advisories = resolve_affected_units(
        tmp_path,
        changes=changes,
        inputs=UnitResolutionInputs(
            config=MaintainerConfig(),
            classifications=(
                _classification("services/api/src/main/java/App.java", "java"),
            ),
            package_workspace=PackageWorkspaceEvidence(),
            java_module_paths=("services/api",),
        ),
    )

    assert [(unit.kind, unit.root) for unit in units] == [
        ("repository", "."),
        ("gradle-module", "services/api"),
    ]
    assert units[0].changed_paths == ("README.md",)
    assert advisories == ()


def test_invalid_or_unmatched_roots_fall_back_with_advisory(tmp_path: Path) -> None:
    change = GitPathChange("src/app.py", "modified")

    units, advisories = resolve_affected_units(
        tmp_path,
        changes=(change,),
        inputs=UnitResolutionInputs(
            config=MaintainerConfig(package_paths=("../outside",)),
            classifications=(_classification("src/app.py", "python"),),
            package_workspace=PackageWorkspaceEvidence(),
            java_module_paths=(),
        ),
    )

    assert units[0].kind == "repository"
    assert units[0].changed_paths == ("src/app.py",)
    assert any("../outside" in advisory for advisory in advisories)


def test_rename_assigns_source_and_destination_independently(tmp_path: Path) -> None:
    change = GitPathChange(
        "packages/new/main.py",
        "renamed",
        old_path="packages/old/main.py",
    )

    units, _ = resolve_affected_units(
        tmp_path,
        changes=(change,),
        inputs=UnitResolutionInputs(
            config=MaintainerConfig(package_paths=("packages/old", "packages/new")),
            classifications=(
                _classification("packages/old/main.py", "python", ChangeKind.RENAMED),
                _classification("packages/new/main.py", "python", ChangeKind.RENAMED),
            ),
            package_workspace=PackageWorkspaceEvidence(),
            java_module_paths=(),
        ),
    )

    assert [(unit.root, unit.changed_paths) for unit in units] == [
        ("packages/new", ("packages/new/main.py",)),
        ("packages/old", ("packages/old/main.py",)),
    ]


def _classification(
    path: str,
    ecosystem: str,
    change_kind: ChangeKind = ChangeKind.MODIFIED,
) -> FileChangeClassification:
    return FileChangeClassification(
        path=path,
        ecosystem=ecosystem,
        role=FileRole.SOURCE,
        change_kind=change_kind,
    )


def _write_package(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{{"name": "{name}"}}\n', encoding="utf-8")
