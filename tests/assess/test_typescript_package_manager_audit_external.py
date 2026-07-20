"""Offline replay tests for public TypeScript audit projections."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent_repair_facts.parsers.typescript_package_manager_audit import parse_audit_report

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_package_manager_audit_external"
NPM_PROJECTION = FIXTURE_ROOT / "npm-node-typescript-boilerplate.json"
PNPM_PROJECTION = FIXTURE_ROOT / "pnpm-eslint-plugin-vitest.json"


@pytest.mark.parametrize(
    ("path", "manager", "repository", "head_commit"),
    (
        (
            NPM_PROJECTION,
            "npm",
            "https://github.com/jsynowiec/node-typescript-boilerplate",
            "550dfd2a976d69254ed71eb6f5a6c5ee20060807",
        ),
        (
            PNPM_PROJECTION,
            "pnpm",
            "https://github.com/vitest-dev/eslint-plugin-vitest",
            "7c697f8a53d7d7551b00ef11217d58cd45a0cf7d",
        ),
    ),
)
def test_pinned_audit_projection_replays_offline(
    path: Path,
    manager: str,
    repository: str,
    head_commit: str,
) -> None:
    """Public pinned projections replay without network or package-manager tools."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    report_text = json.dumps(payload["report"], sort_keys=True, separators=(",", ":"))
    result = parse_audit_report(manager, "root", repository, report_text)

    assert payload["manager"] == manager
    assert payload["repository"] == repository
    assert payload["head_commit"] == head_commit
    assert payload["report_sha256"] == hashlib.sha256(report_text.encode("utf-8")).hexdigest()
    assert payload["report_bytes"] == len(report_text.encode("utf-8"))
    assert result.supported_count == payload["supported_count"]
    assert result.retained_count == payload["retained_count"]
    assert result.omitted_count == payload["omitted_count"]
    assert [finding.package for finding in result.findings] == [
        item["package"] for item in payload["normalized_findings"]
    ]
