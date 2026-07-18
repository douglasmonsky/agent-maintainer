"""Tests pinned public dependency-cruiser compatibility projections."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts.parsers.typescript_dependency_cruiser import (
    parse_dependency_cruiser_json_result,
)

FIXTURE_ROOT = (
    Path(__file__).parents[1]
    / "fixtures"
    / "typescript_dependency_cruiser_external"
)
FIXTURES = (
    ("npm-project.json", "npm"),
    ("pnpm-workspace.json", "pnpm"),
)
PROJECTION_LIMIT = 25
COMMIT_SHA_LENGTH = 40
SHA256_HEX_LENGTH = 64


# docsync:evidence.start evidence.typescript.dependency_cruiser_external_fixtures
@pytest.mark.parametrize(("filename", "package_manager"), FIXTURES)
def test_public_projection_metadata_is_pinned_and_private_path_free(
    filename: str,
    package_manager: str,
) -> None:
    """Compatibility evidence is reproducible, bounded, and safe to commit."""

    fixture = _fixture(filename)
    serialized = json.dumps(fixture)

    assert str(fixture["source_repository"]).startswith("https://github.com/")
    assert len(str(fixture["commit"])) == COMMIT_SHA_LENGTH
    assert str(fixture["collected_at"]).endswith("Z")
    assert fixture["package_manager"] == package_manager
    assert fixture["tool"] == {
        "name": "dependency-cruiser",
        "version": "17.0.2",
    }
    command = fixture["command"]
    assert isinstance(command, list)
    assert command[-3:-1] == ["--output-type", "json"]
    assert str(command[-1]).endswith("/**/*.ts")
    assert int(fixture["exit_code"]) >= 0
    assert int(fixture["supported_finding_count"]) >= int(
        fixture["retained_finding_count"]
    )
    assert int(fixture["retained_finding_count"]) <= PROJECTION_LIMIT
    assert len(str(fixture["config_sha256"])) == SHA256_HEX_LENGTH
    assert len(str(fixture["lockfile_sha256"])) == SHA256_HEX_LENGTH
    if package_manager == "pnpm":
        assert fixture["workspace_manifest_path"] == "pnpm-workspace.yaml"
        assert len(str(fixture["workspace_manifest_sha256"])) == SHA256_HEX_LENGTH
    assert "/Users/" not in serialized
    assert "/private/tmp/" not in serialized


@pytest.mark.parametrize(("filename", "package_manager"), FIXTURES)
def test_public_projection_replays_through_shared_parser(
    filename: str,
    package_manager: str,
) -> None:
    """Retained public violations remain compatible with the shared parser."""

    del package_manager
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
