"""Tests pinned public dependency-cruiser compatibility projections."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast

import pytest

from agent_repair_facts.parsers.typescript_dependency_cruiser import (
    parse_dependency_cruiser_json_result,
)

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_dependency_cruiser_external"
FIXTURES = (
    ("npm-project.json", "npm"),
    ("pnpm-workspace.json", "pnpm"),
)
PROJECTION_LIMIT = 25
COMMIT_SHA_LENGTH = 40
SHA256_HEX_LENGTH = 64


# docsync:evidence.start evidence.typescript.dependency_cruiser_external_fixtures
def _as_int(value: object) -> int:
    """Return an integer fixture field or fail the contract."""

    if isinstance(value, int):
        return value
    raise AssertionError


def _assert_source_metadata(
    fixture: dict[str, object],
    package_manager: str,
) -> None:
    """Check pinned public-source metadata."""

    assert str(fixture["source_repository"]).startswith("https://github.com/")
    assert len(str(fixture["commit"])) == COMMIT_SHA_LENGTH
    assert str(fixture["collected_at"]).endswith("Z")
    assert fixture["package_manager"] == package_manager


def _assert_runtime_metadata(fixture: dict[str, object]) -> None:
    """Check the pinned Node and dependency-cruiser versions."""

    assert fixture["node_version"] == "v26.5.0"
    assert fixture["tool"] == {
        "name": "dependency-cruiser",
        "version": "17.0.2",
    }


def _assert_command_metadata(fixture: dict[str, object]) -> None:
    """Check the replay command is explicit and JSON-producing."""

    command = fixture["command"]
    assert isinstance(command, list)
    assert command[-3:-1] == ["--output-type", "json"]
    assert str(command[-1]).endswith("/**/*.ts")


def _assert_count_metadata(fixture: dict[str, object]) -> None:
    """Check reported and retained finding counts are consistent."""

    supported_count = _as_int(fixture["supported_finding_count"])
    retained_count = _as_int(fixture["retained_finding_count"])
    assert _as_int(fixture["exit_code"]) >= 0
    assert supported_count >= retained_count
    assert retained_count <= PROJECTION_LIMIT


def _assert_workspace_hash(fixture: dict[str, object]) -> None:
    """Check the pnpm workspace manifest fingerprint."""

    assert fixture["workspace_manifest_path"] == "pnpm-workspace.yaml"
    workspace_hash = str(fixture["workspace_manifest_sha256"])
    assert len(workspace_hash) == SHA256_HEX_LENGTH


def _assert_hash_metadata(
    fixture: dict[str, object],
    package_manager: str,
) -> None:
    """Check source inputs and raw output carry pinned fingerprints."""

    assert len(str(fixture["config_sha256"])) == SHA256_HEX_LENGTH
    assert len(str(fixture["lockfile_sha256"])) == SHA256_HEX_LENGTH
    assert len(str(fixture["raw_report_sha256"])) == SHA256_HEX_LENGTH
    assert _as_int(fixture["raw_report_bytes"]) > 0
    if package_manager == "pnpm":
        _assert_workspace_hash(fixture)


def _fixture_strings(value: object) -> list[str]:
    """Return every string nested in one JSON-compatible fixture."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items = cast(list[object], value)
        return [text for item in items for text in _fixture_strings(item)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return [text for item in mapping.values() for text in _fixture_strings(item)]
    return []


def _is_absolute_local_path(value: str) -> bool:
    """Return whether text names an absolute POSIX or Windows path."""

    windows_path = PureWindowsPath(value)
    return (
        PurePosixPath(value).is_absolute() or windows_path.is_absolute() or bool(windows_path.drive)
    )


def _assert_private_path_free(fixture: dict[str, object]) -> None:
    """Check the public projection contains no absolute local paths."""

    private_paths = [value for value in _fixture_strings(fixture) if _is_absolute_local_path(value)]
    assert not private_paths


@pytest.mark.parametrize(("filename", "package_manager"), FIXTURES)
def test_projection_metadata(
    filename: str,
    package_manager: str,
) -> None:
    """Compatibility evidence is reproducible, bounded, and safe to commit."""

    fixture = _fixture(filename)
    _assert_source_metadata(fixture, package_manager)
    _assert_runtime_metadata(fixture)
    _assert_command_metadata(fixture)
    _assert_count_metadata(fixture)
    _assert_hash_metadata(fixture, package_manager)
    _assert_private_path_free(fixture)


@pytest.mark.parametrize(
    "filename",
    tuple(fixture[0] for fixture in FIXTURES),
)
def test_projection_parser_replay(filename: str) -> None:
    """Retained public violations remain compatible with the shared parser."""

    fixture = _fixture(filename)
    violations = fixture["violations"]
    result = parse_dependency_cruiser_json_result(
        json.dumps(
            {
                "summary": {"violations": violations},
                "modules": [],
            }
        )
    )

    assert result.valid is True
    assert result.supported_count == fixture["retained_finding_count"]
    assert len(result.findings) == fixture["retained_finding_count"]


def _fixture(filename: str) -> dict[str, object]:
    """Load one committed public projection."""

    return json.loads((FIXTURE_ROOT / filename).read_text(encoding="utf-8"))


# docsync:evidence.end evidence.typescript.dependency_cruiser_external_fixtures
