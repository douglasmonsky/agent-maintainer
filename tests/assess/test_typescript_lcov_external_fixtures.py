"""Replay pinned public TypeScript LCOV compatibility projections."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast

import pytest

from agent_maintainer.test_intel.typescript_coverage import (
    TypeScriptCoverageRequest,
    build_report,
)
from agent_repair_facts.parsers.typescript_coverage import parse_lcov_records

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_lcov_external"
FIXTURES = (
    ("cmsgov-qpp-measures-data.json", "npm"),
    ("starbeam-pnpm-workspace.json", "pnpm"),
)
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_HEX_RE = re.compile(r"^[0-9a-f]{40}$")


# docsync:evidence.start evidence.typescript.lcov_external_fixtures
@pytest.mark.parametrize(("filename", "package_manager"), FIXTURES)
def test_public_lcov_projection_metadata(filename: str, package_manager: str) -> None:
    """Public projections are pinned, bounded, and provenance-complete."""

    fixture = load_fixture(filename)

    assert str(fixture["source_repository"]).startswith("https://github.com/")
    assert SHA1_HEX_RE.fullmatch(str(fixture["commit"]))
    collected_at = datetime.fromisoformat(str(fixture["collected_at"]))
    assert collected_at.tzinfo is not None
    assert collected_at.utcoffset() == timedelta(0)
    assert fixture["package_manager"] == package_manager
    assert str(fixture["package_manager_version"])
    assert str(fixture["node_version"])
    assert SHA256_HEX_RE.fullmatch(str(fixture["lockfile_sha256"]))
    assert SHA256_HEX_RE.fullmatch(str(fixture["raw_lcov_sha256"]))
    assert SHA1_HEX_RE.fullmatch(str(fixture["artifact_git_blob_sha1"]))
    assert positive_int(fixture["raw_lcov_bytes"])
    assert coverage_provenance_is_explicit(fixture)
    assert fixture["projected_record_count"] == len(
        parse_lcov_records(str(fixture["lcov_projection"]))
    )
    assert not absolute_local_paths(fixture)


@pytest.mark.parametrize("filename", tuple(item[0] for item in FIXTURES))
def test_public_lcov_projection_replays_changed_line_math(
    filename: str,
    tmp_path: Path,
) -> None:
    """Pinned npm and pnpm LCOV records replay through the real adapter."""

    fixture = load_fixture(filename)
    changed_lines = string_line_map(fixture["changed_lines"])
    create_repo(tmp_path)
    for relative, lines in changed_lines.items():
        write_numbered_source(tmp_path / relative, max(lines))
    commit_all(tmp_path)
    for relative, lines in changed_lines.items():
        change_source_lines(tmp_path / relative, lines)
    artifact_path = Path(str(fixture["artifact_path"]))
    artifact = tmp_path / artifact_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(str(fixture["lcov_projection"]), encoding="utf-8")

    report = build_report(
        TypeScriptCoverageRequest(
            repo_root=tmp_path,
            lcov_path=artifact_path,
            source_root=Path(str(fixture["source_root"])),
        )
    )
    expected = object_mapping(fixture["expected"])

    assert report.changed_source == tuple(sorted(changed_lines))
    assert not report.missing_from_lcov
    assert report.executable_changed_lines == expected["executable_changed_lines"]
    assert report.covered_changed_lines == expected["covered_changed_lines"]
    assert report.changed_line_coverage == expected["changed_line_coverage"]


def load_fixture(filename: str) -> dict[str, object]:
    """Load one committed projection."""

    return cast(
        dict[str, object],
        json.loads((FIXTURE_ROOT / filename).read_text(encoding="utf-8")),
    )


def positive_int(value: object) -> bool:
    """Return whether a fixture value is a positive integer."""

    return isinstance(value, int) and value > 0


def coverage_provenance_is_explicit(fixture: dict[str, object]) -> bool:
    """Return whether producer and generation-command provenance are explicit."""

    producer = object_mapping(fixture["coverage_producer"])
    producer_declared = bool(str(producer.get("name", ""))) and bool(
        str(producer.get("version", ""))
    )
    command = fixture.get("command")
    declared_command = fixture.get("declared_command")
    unavailable = fixture.get("generation_status")
    command_declared = (
        isinstance(command, list)
        and bool(command)
        and isinstance(declared_command, str)
        and bool(declared_command)
    )
    return producer_declared and (
        command_declared or unavailable == "exact command not declared at pinned commit"
    )


def object_mapping(value: object) -> dict[str, object]:
    """Return a fixture object mapping."""

    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def string_line_map(value: object) -> dict[str, tuple[int, ...]]:
    """Return changed-line fixture metadata with runtime validation."""

    result: dict[str, tuple[int, ...]] = {}
    for path, raw_lines in object_mapping(value).items():
        assert isinstance(raw_lines, list)
        lines = cast(list[object], raw_lines)
        assert all(isinstance(line, int) and line > 0 for line in lines)
        result[path] = tuple(cast(list[int], lines))
    return result


def nested_strings(value: object) -> list[str]:
    """Return every string in a JSON-compatible value."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items = cast(list[object], value)
        return [text for item in items for text in nested_strings(item)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return [text for item in mapping.values() for text in nested_strings(item)]
    return []


def absolute_local_paths(value: object) -> list[str]:
    """Return absolute POSIX or Windows paths from fixture strings."""

    return [
        text
        for text in nested_strings(value)
        if PurePosixPath(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
        or bool(PureWindowsPath(text).drive)
    ]


def write_numbered_source(path: Path, line_count: int) -> None:
    """Write a source file with stable executable-shaped lines."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"line{line}();\n" for line in range(1, line_count + 1)),
        encoding="utf-8",
    )


def change_source_lines(path: Path, changed_lines: tuple[int, ...]) -> None:
    """Change exact lines while preserving all line numbers."""

    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number in changed_lines:
        lines[line_number - 1] = f"changed{line_number}();"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_repo(path: Path) -> None:
    """Initialize one temporary Git repository."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.invalid")
    run_git(path, "config", "user.name", "Agent Maintainer Test")


def commit_all(path: Path) -> None:
    """Commit all source fixtures."""

    run_git(path, "add", "--", ".")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run Git in a temporary repository."""

    subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


# docsync:evidence.end evidence.typescript.lcov_external_fixtures
