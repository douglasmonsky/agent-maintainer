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
        (
            "SF:src/app.ts\nDA:1,0\nend_of_record\n"
            f"SF:{source_path}\nDA:1,3\nend_of_record\n"
        ),
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

    report = build_report(
        TypeScriptCoverageRequest(repo_root=tmp_path, staged=True)
    )

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
    with pytest.raises(TypeScriptCoverageError, match="Git diff"):
        build_report(
            TypeScriptCoverageRequest(repo_root=tmp_path, base_ref="missing-ref")
        )


def test_report_rejects_paths_outside_repository(tmp_path: Path) -> None:
    """Artifact and source-root inputs are confined after resolution."""

    create_repo(tmp_path)
    outside = tmp_path.parent / "outside-lcov.info"
    outside.write_text("SF:src/app.ts\nDA:1,1\n", encoding="utf-8")

    with pytest.raises(TypeScriptCoverageError, match="inside the repository"):
        build_report(
            TypeScriptCoverageRequest(repo_root=tmp_path, lcov_path=outside)
        )
    with pytest.raises(TypeScriptCoverageError, match="inside the repository"):
        build_report(
            TypeScriptCoverageRequest(repo_root=tmp_path, source_root=tmp_path.parent)
        )


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


def test_changed_source_rejects_unsafe_or_excessive_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git paths are control-safe and bounded before diff-hunk mapping."""

    assert is_typescript_source("src/unsafe\nname.ts") is False
    assert is_typescript_source(f"src/{'x' * 501}.ts") is False
    stdout = "\0".join(
        f"src/file-{index:03d}.ts"
        for index in range(typescript_coverage.MAX_CHANGED_SOURCE_FILES + 1)
    )
    monkeypatch.setattr(
        typescript_coverage.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout, ""),
    )

    with pytest.raises(TypeScriptCoverageError, match="too many TypeScript source files"):
        changed_typescript_source_paths(tmp_path, base_ref="HEAD", staged=False)


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
