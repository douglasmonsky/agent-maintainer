"""Tests provider-aware changed-file classification."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.file_changes import (
    ChangedPath,
    _select_classification,  # pyright: ignore[reportPrivateUsage]
    classify_changed_path,
    classify_changed_paths,
)
from agent_maintainer.ecosystems.models import (
    ChangeKind,
    FileChangeClassification,
    FileClassification,
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
    assert classify_changed_path("native/app/main.rs", "modified", config) is None

    enabled = replace(config, enable_typescript=True)

    typescript = classify_changed_path("src/app.ts", "modified", enabled)

    _assert_change(typescript, ecosystem="typescript", role=FileRole.SOURCE)
    assert classify_changed_path("native/app/main.rs", "modified", enabled) is None


def test_batch_change_classification_order() -> None:
    """Batch helper preserves changed-path order and change metadata."""
    config = replace(MaintainerConfig(), enable_typescript=True)

    classifications = classify_changed_paths(
        (
            ChangedPath("src/app.ts", ChangeKind.ADDED),
            ChangedPath("native/app/main_test.rs", ChangeKind.MODIFIED),
            ChangedPath("notes/random.log", ChangeKind.DELETED),
        ),
        config,
    )

    assert [(item.ecosystem, item.role, item.change_kind) for item in classifications] == [
        ("typescript", FileRole.SOURCE, ChangeKind.ADDED),
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


def test_dot_directory_config_classification_preserves_path() -> None:
    """Dot-prefixed repo paths keep their exact Git path for report joins."""

    classification = classify_changed_path(
        ".docsync/trace.yml",
        ChangeKind.MODIFIED,
        MaintainerConfig(),
    )

    _assert_change(classification, ecosystem="python", role=FileRole.CONFIG)
    assert classification is not None
    assert classification.path == ".docsync/trace.yml"


def test_typescript_dot_directory_classification_preserves_path() -> None:
    """Enabled TypeScript classification does not strip dot-directory prefixes."""

    classification = classify_changed_path(
        ".storybook/main.ts",
        ChangeKind.MODIFIED,
        replace(MaintainerConfig(), enable_typescript=True),
    )

    _assert_change(classification, ecosystem="typescript", role=FileRole.SOURCE)
    assert classification is not None
    assert classification.path == ".storybook/main.ts"


def test_header_role_wins_over_shared_docs_candidate() -> None:
    """C/C++ headers remain high confidence for shared repository paths."""
    selected = _select_classification(
        (
            FileClassification("include/api.hpp", "python", FileRole.DOCS),
            FileClassification("include/api.hpp", "cpp", FileRole.HEADER),
        ),
    )

    assert selected is not None
    assert selected.ecosystem == "cpp"
    assert selected.role is FileRole.HEADER


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
