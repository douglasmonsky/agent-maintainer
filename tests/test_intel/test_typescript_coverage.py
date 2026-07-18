"""Tests for advisory TypeScript LCOV changed-line coverage."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.test_intel import typescript_coverage
from agent_maintainer.test_intel.typescript_coverage import (
    TypeScriptCoverageError,
    TypeScriptCoverageRequest,
    build_report,
    changed_typescript_source_paths,
    is_typescript_source,
    normalize_source_path,
)

EXPECTED_EXECUTABLE_LINES = 3
EXPECTED_COVERED_LINES = 2
EXPECTED_WEIGHTED_PERCENT = 66.67
FULL_COVERAGE_PERCENT = 100.0


def test_report_uses_weighted_executable_changed_lines(tmp_path: Path) -> None:
    """Aggregate coverage counts executable changed lines across files."""

    create_repo(tmp_path)
    write_source(tmp_path, "packages/web/src/a.ts", "one();\ntwo();\n// old\n")
    write_source(tmp_path, "packages/web/src/b.ts", "old();\n")
    write_source(tmp_path, "packages/web/src/missing.ts", "old();\n")
    commit_all(tmp_path)
    write_source(tmp_path, "packages/web/src/a.ts", "ONE();\nTWO();\n// new\n")
    write_source(tmp_path, "packages/web/src/b.ts", "NEW();\n")
    write_source(tmp_path, "packages/web/src/missing.ts", "NEW();\n")
    write_lcov(
        tmp_path,
        """
SF:packages/web/src/a.ts
DA:1,2
DA:2,1
end_of_record
SF:packages/web/src/b.ts
DA:1,0
end_of_record
""".lstrip(),
    )

    report = build_report(TypeScriptCoverageRequest(repo_root=tmp_path))

    assert report.changed_source == (
        "packages/web/src/a.ts",
        "packages/web/src/b.ts",
        "packages/web/src/missing.ts",
    )
    assert report.missing_from_lcov == ("packages/web/src/missing.ts",)
    assert report.executable_changed_lines == EXPECTED_EXECUTABLE_LINES
    assert report.covered_changed_lines == EXPECTED_COVERED_LINES
    assert report.missed_changed_lines == 1
    assert report.changed_line_coverage == EXPECTED_WEIGHTED_PERCENT
    assert tuple((fact.path, fact.changed_line_coverage) for fact in report.files) == (
        ("packages/web/src/a.ts", 100.0),
        ("packages/web/src/b.ts", 0.0),
    )


def test_report_maps_workspace_and_absolute_lcov_sources(tmp_path: Path) -> None:
    """Explicit source roots map relative records and accept local absolutes."""

    create_repo(tmp_path)
    source_path = tmp_path / "packages/web/src/app.ts"
    write_source(tmp_path, "packages/web/src/app.ts", "old();\n")
    commit_all(tmp_path)
    write_source(tmp_path, "packages/web/src/app.ts", "new();\n")
    write_lcov(
        tmp_path,
        (f"SF:src/app.ts\nDA:1,0\nend_of_record\nSF:{source_path}\nDA:1,3\nend_of_record\n"),
    )

    report = build_report(
        TypeScriptCoverageRequest(
            repo_root=tmp_path,
            source_root=Path("packages/web"),
        )
    )

    assert report.covered_changed_lines == 1
    assert report.changed_line_coverage == FULL_COVERAGE_PERCENT
    assert report.files[0].path == "packages/web/src/app.ts"


def test_report_is_advisory_when_changed_lines_are_not_executable(tmp_path: Path) -> None:
    """A matched record without executable changed lines reports unknown."""

    create_repo(tmp_path)
    write_source(tmp_path, "src/app.ts", "// old\n")
    commit_all(tmp_path)
    write_source(tmp_path, "src/app.ts", "// new\n")
    write_lcov(tmp_path, "SF:src/app.ts\nDA:8,1\nend_of_record\n")

    report = build_report(TypeScriptCoverageRequest(repo_root=tmp_path))

    assert report.executable_changed_lines == 0
    assert report.changed_line_coverage is None
    assert report.files[0].changed_line_coverage is None
    assert "advisory" in report.note.lower()


def test_report_uses_staged_diff_and_excludes_non_source_roles(tmp_path: Path) -> None:
    """Staged discovery includes source and excludes tests/generated/deleted."""

    create_repo(tmp_path)
    write_source(tmp_path, "src/app.ts", "old();\n")
    write_source(tmp_path, "src/app.test.ts", "oldTest();\n")
    write_source(tmp_path, "src/generated/client.ts", "oldGenerated();\n")
    write_source(tmp_path, "src/deleted.ts", "oldDeleted();\n")
    commit_all(tmp_path)
    write_source(tmp_path, "src/app.ts", "new();\n")
    write_source(tmp_path, "src/app.test.ts", "newTest();\n")
    write_source(tmp_path, "src/generated/client.ts", "newGenerated();\n")
    (tmp_path / "src/deleted.ts").unlink()
    run_git(tmp_path, "add", "--", "src")
    write_lcov(tmp_path, "SF:src/app.ts\nDA:1,1\nend_of_record\n")

    report = build_report(TypeScriptCoverageRequest(repo_root=tmp_path, staged=True))

    assert report.changed_source == ("src/app.ts",)
    assert report.changed_line_coverage == FULL_COVERAGE_PERCENT


@pytest.mark.parametrize(
    "source",
    (
        "../outside.ts",
        "/private/outside.ts",
        "C:/outside.ts",
        "src/unsafe\x00.ts",
    ),
)
def test_report_ignores_unsafe_lcov_sources(tmp_path: Path, source: str) -> None:
    """Unsafe LCOV paths never match changed repository files."""

    create_repo(tmp_path)
    write_source(tmp_path, "src/app.ts", "old();\n")
    commit_all(tmp_path)
    write_source(tmp_path, "src/app.ts", "new();\n")
    write_lcov(
        tmp_path,
        f"SF:{source}\nDA:1,1\nend_of_record\nSF:src/safe.ts\nDA:2,1\nend_of_record\n",
    )

    report = build_report(TypeScriptCoverageRequest(repo_root=tmp_path))

    assert report.missing_from_lcov == ("src/app.ts",)
    assert report.executable_changed_lines == 0


def test_report_rejects_unusable_artifacts_and_invalid_git_refs(tmp_path: Path) -> None:
    """Explicit report failures are concise rather than silently unknown."""

    create_repo(tmp_path)
    write_source(tmp_path, "src/app.ts", "old();\n")
    commit_all(tmp_path)
    write_source(tmp_path, "src/app.ts", "new();\n")
    write_lcov(tmp_path, "TN:empty\n")

    with pytest.raises(TypeScriptCoverageError, match="usable LCOV"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path))

    write_lcov(tmp_path, "SF:src/app.ts\nDA:1,1\nend_of_record\n")
    with pytest.raises(TypeScriptCoverageError, match="Git ref"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path, base_ref="missing-ref"))


@pytest.mark.parametrize("base_ref", ("--stat", "--ext-diff", "--output=unsafe.patch"))
def test_report_rejects_option_shaped_git_refs(tmp_path: Path, base_ref: str) -> None:
    """Git options are rejected before they can reach a diff command."""

    create_repo(tmp_path)
    write_source(tmp_path, "src/app.ts", "old();\n")
    commit_all(tmp_path)
    write_source(tmp_path, "src/app.ts", "new();\n")
    write_lcov(tmp_path, "SF:src/app.ts\nDA:1,1\nend_of_record\n")

    with pytest.raises(TypeScriptCoverageError, match="Git ref"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path, base_ref=base_ref))

    assert not (tmp_path / "unsafe.patch").exists()


def test_report_rejects_paths_outside_repository(tmp_path: Path) -> None:
    """Artifact and source-root inputs are confined after resolution."""

    create_repo(tmp_path)
    outside = tmp_path.parent / "outside-lcov.info"
    outside.write_text("SF:src/app.ts\nDA:1,1\n", encoding="utf-8")

    with pytest.raises(TypeScriptCoverageError, match="inside the repository"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path, lcov_path=outside))
    with pytest.raises(TypeScriptCoverageError, match="inside the repository"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path, source_root=tmp_path.parent))


def test_report_confines_symlinks_but_accepts_internal_artifact_link(tmp_path: Path) -> None:
    """Resolved artifact, source-root, and LCOV paths stay inside the repository."""

    create_repo(tmp_path)
    outside_artifact = tmp_path.parent / f"{tmp_path.name}-outside.lcov"
    outside_source = tmp_path.parent / f"{tmp_path.name}-outside-source"
    outside_artifact.write_text("SF:src/app.ts\nDA:1,1\n", encoding="utf-8")
    outside_source.mkdir()
    (tmp_path / "artifact-link.lcov").symlink_to(outside_artifact)
    (tmp_path / "source-link").symlink_to(outside_source, target_is_directory=True)

    with pytest.raises(TypeScriptCoverageError, match="inside the repository"):
        build_report(
            TypeScriptCoverageRequest(repo_root=tmp_path, lcov_path=Path("artifact-link.lcov"))
        )
    with pytest.raises(TypeScriptCoverageError, match="inside the repository"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path, source_root=Path("source-link")))

    internal_artifact = tmp_path / "coverage/real.info"
    internal_artifact.parent.mkdir(parents=True)
    internal_artifact.write_text("SF:src/app.ts\nDA:1,1\n", encoding="utf-8")
    internal_link = tmp_path / "coverage/link.info"
    internal_link.symlink_to(internal_artifact)
    assert typescript_coverage.read_lcov_artifact(internal_link).startswith("SF:src/app.ts")


def test_lcov_source_symlink_cannot_escape_repository(tmp_path: Path) -> None:
    """An LCOV source symlink is ignored when its target escapes the repository."""

    outside_source = tmp_path.parent / f"{tmp_path.name}-outside.ts"
    outside_source.write_text("outside();\n", encoding="utf-8")
    source_link = tmp_path / "src/escape.ts"
    source_link.parent.mkdir(parents=True)
    source_link.symlink_to(outside_source)

    assert normalize_source_path("src/escape.ts", tmp_path, tmp_path) is None


def test_report_rejects_oversized_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bounded artifact reads fail before Git or parser work."""

    create_repo(tmp_path)
    write_lcov(tmp_path, "SF:src/app.ts\nDA:1,1\n")
    monkeypatch.setattr(typescript_coverage, "MAX_LCOV_BYTES", 8)

    with pytest.raises(TypeScriptCoverageError, match="10 MiB limit"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path))


def test_changed_source_rejects_unsafe_paths_without_truncating_valid_diffs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git paths are control-safe without truncating valid large diffs."""

    assert is_typescript_source("src/unsafe\nname.ts") is False
    assert is_typescript_source(f"src/{'x' * 501}.ts") is False
    stdout = "\0".join(
        f"src/file-{index:03d}.ts" for index in range(typescript_coverage.MAX_FILE_FACTS + 1)
    )

    def completed_diff(
        *_args: object,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git", "diff"], 0, stdout, "")

    monkeypatch.setattr(
        typescript_coverage.subprocess,
        "run",
        completed_diff,
    )

    paths = changed_typescript_source_paths(tmp_path, base_ref="HEAD", staged=False)

    assert len(paths) == typescript_coverage.MAX_FILE_FACTS + 1


def test_report_aggregates_all_files_before_retaining_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A large valid diff keeps exact totals and retains only 500 facts."""

    create_repo(tmp_path)
    paths = tuple(
        f"src/file-{index:03d}.ts" for index in range(typescript_coverage.MAX_FILE_FACTS + 1)
    )
    write_lcov(
        tmp_path,
        "".join(f"SF:{path}\nDA:1,1\nend_of_record\n" for path in paths),
    )

    def changed_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return paths

    def changed_lines(
        _self: object,
        _changed_source: tuple[str, ...],
        *,
        base_ref: str,
        staged: bool,
    ) -> dict[str, frozenset[int]]:
        del base_ref, staged
        return {path: frozenset((1,)) for path in paths}

    monkeypatch.setattr(
        typescript_coverage,
        "changed_typescript_source_paths",
        changed_paths,
    )
    monkeypatch.setattr(
        "agent_maintainer.test_intel.typescript_coverage._GitDiff.changed_line_numbers",
        changed_lines,
    )

    report = build_report(TypeScriptCoverageRequest(repo_root=tmp_path, staged=True))

    assert report.executable_changed_lines == len(paths)
    assert report.covered_changed_lines == len(paths)
    assert report.matched_file_count == len(paths)
    assert len(report.files) == typescript_coverage.MAX_FILE_FACTS


@pytest.mark.parametrize(
    "failure",
    (
        subprocess.CalledProcessError(1, ["git", "diff"]),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid byte"),
    ),
)
def test_report_surfaces_strict_hunk_mapping_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    """The explicit report never converts a failed hunk diff into unknown coverage."""

    create_repo(tmp_path)
    write_lcov(tmp_path, "SF:src/app.ts\nDA:1,1\nend_of_record\n")

    def changed_paths(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        return ("src/app.ts",)

    monkeypatch.setattr(
        typescript_coverage,
        "changed_typescript_source_paths",
        changed_paths,
    )

    def fail_diff(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise failure

    monkeypatch.setattr(typescript_coverage.subprocess, "run", fail_diff)

    with pytest.raises(TypeScriptCoverageError, match="Git diff"):
        build_report(TypeScriptCoverageRequest(repo_root=tmp_path, staged=True))


def create_repo(path: Path) -> None:
    """Initialize a temporary Git repository."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.invalid")
    run_git(path, "config", "user.name", "Agent Maintainer Test")


def write_source(root: Path, relative: str, content: str) -> None:
    """Write one repository source fixture."""

    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_lcov(root: Path, content: str) -> None:
    """Write the conventional LCOV artifact."""

    path = root / "coverage/lcov.info"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commit_all(path: Path) -> None:
    """Commit all current fixture files."""

    run_git(path, "add", "--", ".")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run Git in one temporary repository."""

    subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
