"""Tests provider-aware changed-file classification."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.file_changes import (
    ChangedPath,
    classify_changed_path,
    classify_changed_paths,
)
from agent_maintainer.ecosystems.models import (
    ChangeKind,
    FileChangeClassification,
    FileRole,
)


def test_python_change_roots() -> None:
    """Python source and test roles continue to follow configured roots."""
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",))

    source = classify_changed_path("src/pkg/app.py", "modified", config)
    test = classify_changed_path("tests/test_app.py", ChangeKind.ADDED, config)

    _assert_change(
        source,
        ecosystem="python",
        role=FileRole.SOURCE,
        change_kind=ChangeKind.MODIFIED,
    )
    _assert_change(
        test,
        ecosystem="python",
        role=FileRole.TEST,
        change_kind=ChangeKind.ADDED,
    )


def test_experimental_changes_need_enabled() -> None:
    """Experimental ecosystems do not become implicit policy inputs."""
    config = MaintainerConfig()

    assert classify_changed_path("src/app.ts", "modified", config) is None
    assert classify_changed_path("cmd/server/main.go", "modified", config) is None

    enabled = replace(config, enable_typescript=True, enable_go=True)

    typescript = classify_changed_path("src/app.ts", "modified", enabled)
    go = classify_changed_path("cmd/server/main.go", "modified", enabled)

    _assert_change(typescript, ecosystem="typescript", role=FileRole.SOURCE)
    _assert_change(go, ecosystem="go", role=FileRole.SOURCE)


def test_batch_change_classification_order() -> None:
    """Batch helper preserves changed-path order and change metadata."""
    config = replace(MaintainerConfig(), enable_typescript=True, enable_go=True)

    classifications = classify_changed_paths(
        (
            ChangedPath("src/app.ts", ChangeKind.ADDED),
            ChangedPath("internal/app/handler_test.go", ChangeKind.MODIFIED),
            ChangedPath("notes/random.log", ChangeKind.DELETED),
        ),
        config,
    )

    assert [(item.ecosystem, item.role, item.change_kind) for item in classifications] == [
        ("typescript", FileRole.SOURCE, ChangeKind.ADDED),
        ("go", FileRole.TEST, ChangeKind.MODIFIED),
    ]


def test_unknown_change_kind_is_explicit() -> None:
    """Unexpected external change labels do not crash classification."""
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",))

    source = classify_changed_path("src/pkg/app.py", "copied", config)

    assert source is not None
    assert source.change_kind == ChangeKind.UNKNOWN


def test_renamed_change_kind_is_supported() -> None:
    """Rename changes remain explicit for future policy reports."""
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",))

    source = classify_changed_path("src/pkg/app.py", ChangeKind.RENAMED, config)

    assert source is not None
    assert source.change_kind == ChangeKind.RENAMED


def _assert_change(
    actual: FileChangeClassification | None,
    *,
    ecosystem: str,
    role: FileRole,
    change_kind: ChangeKind | None = None,
) -> None:
    """Assert relevant changed-file classification fields."""
    assert actual is not None
    assert actual.ecosystem == ecosystem
    assert actual.role == role
    if change_kind is not None:
        assert actual.change_kind == change_kind
