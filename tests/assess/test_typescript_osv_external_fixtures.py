"""Validate recorded public-repository OSV Scanner compatibility evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import cast

import pytest

from agent_repair_facts.parsers import osv_scanner

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_osv_external"
EXPECTED_FIXTURES = {
    "eslint-plugin-vitest.json": (
        "https://github.com/vitest-dev/eslint-plugin-vitest",
        "7c697f8a53d7d7551b00ef11217d58cd45a0cf7d",
        "pnpm-lock.yaml",
        "pnpm@10.18.3",
    ),
    "node-typescript-boilerplate.json": (
        "https://github.com/jsynowiec/node-typescript-boilerplate",
        "550dfd2a976d69254ed71eb6f5a6c5ee20060807",
        "package-lock.json",
        "npm",
    ),
}


def load_fixture(name: str) -> dict[str, object]:
    """Load one recorded public OSV Scanner fixture."""

    payload = json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


# docsync:evidence.start evidence.typescript.osv_external_fixtures
@pytest.mark.parametrize(("name", "source"), EXPECTED_FIXTURES.items())
def test_public_osv_fixture_is_pinned_and_replayable(
    name: str,
    source: tuple[str, str, str, str],
) -> None:
    """Public captures pin source, command, hashes, and normalized counts."""

    fixture = load_fixture(name)
    repository, commit, lockfile, package_manager = source

    assert fixture["schema_version"] == 1
    assert fixture["source_repository"] == repository
    assert fixture["commit"] == commit
    assert fixture["lockfile_path"] == lockfile
    assert fixture["package_manager"] == package_manager
    assert fixture["scanner_version"]
    assert fixture["capture_command"] == [
        "osv-scanner",
        "scan",
        "source",
        "-r",
        ".",
        "--format",
        "json",
    ]
    assert fixture["exit_code"] in (0, 1)
    assert fixture["lockfile_sha256"]
    assert fixture["raw_report_sha256"]
    assert fixture["projection_method"] == "parser-consumed-fields-v1"

    parsed = osv_scanner.parse_osv_payload(fixture["projection"])

    assert parsed.valid is True
    assert parsed.supported_count == fixture["supported_finding_count"]
    assert len(parsed.findings) == fixture["retained_finding_count"]
    assert len(parsed.findings) <= osv_scanner.OSV_FACT_LIMIT


def test_public_osv_fixtures_contain_no_temporary_paths() -> None:
    """Recorded fixtures expose only safe repository-relative source paths."""

    for name in EXPECTED_FIXTURES:
        fixture = load_fixture(name)
        serialized = json.dumps(fixture, sort_keys=True)
        projection = cast(dict[str, object], fixture["projection"])
        results = cast(list[dict[str, object]], projection["results"])

        assert "/private/tmp/" not in serialized
        assert "/Users/" not in serialized
        assert re.search(r'"[A-Za-z]:[\\\\/]', serialized) is None
        for result in results:
            source = cast(dict[str, object], result["source"])
            path = PurePosixPath(str(source["path"]))
            assert not path.is_absolute()
            assert ".." not in path.parts


# docsync:evidence.end evidence.typescript.osv_external_fixtures
