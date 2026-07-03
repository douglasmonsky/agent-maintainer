"""Tests for recorded external TypeScript reviewability comparison evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BOILERPLATE_CHANGED_FILES = 13
BOILERPLATE_CLASSIFIED_FILES = 11
BOILERPLATE_UNCLASSIFIED_FILES = 2
VITEST_CHANGED_FILES = 2
VITEST_FIXTURE = Path(
    "tests/fixtures/typescript_external_reviewability/"
    "eslint_plugin_vitest_7c697f8_reviewability.json",
)
BOILERPLATE_FIXTURE = Path(
    "tests/fixtures/typescript_external_reviewability/"
    "node_typescript_boilerplate_550dfd2_reviewability.json",
)


# docsync:evidence.start evidence.typescript.external_reviewability_comparison
def test_external_typescript_reviewability_comparison_stays_low_noise() -> None:
    """Recorded public-repo TypeScript source/test diff has no advisories."""

    fixture = _load_fixture(VITEST_FIXTURE)
    source = fixture["source"]
    payload = fixture["reviewability"]

    assert source["repository"] == "https://github.com/vitest-dev/eslint-plugin-vitest"
    assert source["head_commit"] == ("7c697f8a53d7d7551b00ef11217d58cd45a0cf7d")
    assert payload["advisory_findings"] == []
    assert payload["total_changed_files"] == VITEST_CHANGED_FILES
    assert payload["classified_files"] == VITEST_CHANGED_FILES
    assert payload["unclassified_files"] == 0
    assert _counts(payload["by_role"]) == {"source": 1, "test": 1}
    assert payload["provider_summaries"] == [
        {
            "broad_suppressions": 0,
            "changed_files": 2,
            "ecosystem": "typescript",
            "source_files": 1,
            "source_lines": 2,
            "test_files": 1,
            "test_lines": 27,
        },
    ]


def test_external_node_boilerplate_vitest_migration_stays_low_noise() -> None:
    """Recorded Node boilerplate test-runner migration stays advisory-only."""

    fixture = _load_fixture(BOILERPLATE_FIXTURE)
    source = fixture["source"]
    payload = fixture["reviewability"]

    assert source["repository"] == ("https://github.com/jsynowiec/node-typescript-boilerplate")
    assert source["head_subject"] == "Switch from Jest to Vitest (#56)"
    assert payload["advisory_findings"] == []
    assert payload["total_changed_files"] == BOILERPLATE_CHANGED_FILES
    assert payload["classified_files"] == BOILERPLATE_CLASSIFIED_FILES
    assert payload["unclassified_files"] == BOILERPLATE_UNCLASSIFIED_FILES
    assert _counts(payload["by_role"]) == {
        "config": 6,
        "dependency": 1,
        "docs": 1,
        "source": 1,
        "test": 2,
    }
    assert payload["provider_summaries"] == [
        {
            "broad_suppressions": 0,
            "changed_files": 4,
            "ecosystem": "typescript",
            "source_files": 1,
            "source_lines": 4,
            "test_files": 2,
            "test_lines": 82,
        },
    ]


def test_external_typescript_reviewability_fixture_records_repro_command() -> None:
    """Recorded comparison keeps enough metadata for manual reproduction."""

    source = _load_fixture(VITEST_FIXTURE)["source"]

    assert source["base_commit"] == "8fff9690c0c4008f93a636a62425dbe520ec7ce7"
    assert source["command"] == (
        "python -m agent_maintainer assess reviewability --target <clone> --base-ref HEAD~1 --json"
    )
    assert source["temporary_config"] == {
        "enable_typescript": True,
        "typescript_lint_command": ["pnpm", "lint"],
        "typescript_test_command": ["pnpm", "test"],
        "typescript_typecheck_command": ["pnpm", "typecheck"],
    }


def test_external_node_boilerplate_fixture_records_repro_command() -> None:
    """Recorded Node boilerplate comparison keeps reproduction metadata."""

    source = _load_fixture(BOILERPLATE_FIXTURE)["source"]

    assert source["base_commit"] == "e2e8c78f0c5ff7e0228f53e6d0cc772241e933e2"
    assert source["head_commit"] == "550dfd2a976d69254ed71eb6f5a6c5ee20060807"
    assert source["temporary_config"] == {
        "enable_typescript": True,
        "typescript_lint_command": ["npm", "run", "lint"],
        "typescript_test_command": ["npm", "test"],
        "typescript_typecheck_command": ["npm", "run", "typecheck"],
    }


# docsync:evidence.end evidence.typescript.external_reviewability_comparison


def _load_fixture(path: Path) -> dict[str, Any]:
    """Load recorded external comparison fixture."""

    return json.loads(path.read_text(encoding="utf-8"))


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    """Return JSON count entries as a mapping."""

    return {item["key"]: item["count"] for item in items}
