"""Validate recorded public-repository Knip compatibility evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from agent_repair_facts.parsers import typescript_knip

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_knip_external"
EXPECTED_FIXTURES = {
    "tanstack-query.json": (
        "https://github.com/TanStack/query",
        "97db5d244715642fb63d9ce78566aa632cdfdc07",
    ),
    "astro.json": (
        "https://github.com/withastro/astro",
        "91992ef2ccd9a90fa4270633eb4f5d3b811bf315",
    ),
}


def load_fixture(name: str) -> dict[str, object]:
    """Load one recorded public Knip fixture."""

    payload = json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


# docsync:evidence.start evidence.typescript.knip_external_fixtures
@pytest.mark.parametrize(("name", "source"), EXPECTED_FIXTURES.items())
def test_public_knip_fixture_is_pinned_and_replayable(
    name: str,
    source: tuple[str, str],
) -> None:
    """Public captures pin source, command, hashes, and normalized counts."""

    fixture = load_fixture(name)
    repository, commit = source
    command = fixture["command"]

    assert fixture["schema_version"] == 1
    assert fixture["source_repository"] == repository
    assert fixture["commit"] == commit
    assert command == ["pnpm", "exec", "knip", "--reporter", "json"]
    assert fixture["exit_code"] in (0, 1)
    assert fixture["config_sha256"]
    assert fixture["lockfile_sha256"]
    assert fixture["package_manager"]
    assert fixture["node_version"]
    assert fixture["knip_version"]

    result = typescript_knip.parse_knip_json_result(str(fixture["stdout"]))

    assert result.valid is True
    assert result.supported_count == fixture["supported_finding_count"]
    assert len(result.findings) == fixture["retained_finding_count"]
    assert len(result.findings) <= typescript_knip.KNIP_FACT_LIMIT


def test_public_knip_fixtures_contain_no_temporary_paths() -> None:
    """Recorded fixtures do not expose local checkout or cache paths."""

    for name in EXPECTED_FIXTURES:
        serialized = json.dumps(load_fixture(name), sort_keys=True)
        assert "/private/tmp/" not in serialized
        assert "/Users/" not in serialized


# docsync:evidence.end evidence.typescript.knip_external_fixtures
