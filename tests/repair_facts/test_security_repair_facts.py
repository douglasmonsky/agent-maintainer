"""Tests structured dependency-security repair facts."""

from __future__ import annotations

import json
from pathlib import Path

from agent_repair_facts import registry


def test_pip_audit_artifact_emits_one_fact_per_vulnerability() -> None:
    """Pip-audit JSON preserves package, advisory, alias, and fix details."""

    payload = {
        "dependencies": [
            {
                "name": "demo",
                "version": "1.0",
                "vulns": [
                    {
                        "id": "PYSEC-2026-1",
                        "aliases": ["CVE-2026-1000", "GHSA-demo"],
                        "fix_versions": ["1.1", "2.0"],
                        "description": "demo vulnerability",
                    }
                ],
            }
        ]
    }

    assert registry.artifact_facts_from_text(
        "pip-audit",
        Path(".verify-logs/pip-audit.json"),
        json.dumps(payload),
    ) == [
        {
            "check": "pip-audit",
            "path": None,
            "line": None,
            "column": None,
            "symbol": "PYSEC-2026-1",
            "message": (
                "demo 1.0: PYSEC-2026-1 "
                "(CVE-2026-1000, GHSA-demo); fix: 1.1, 2.0; demo vulnerability"
            ),
            "severity": "error",
        }
    ]


def test_pip_audit_artifact_ignores_empty_or_malformed_payloads() -> None:
    """Non-finding artifacts do not produce generic fallback facts."""

    path = Path(".verify-logs/pip-audit.json")

    assert (
        registry.artifact_facts_from_text(
            "pip-audit",
            path,
            '{"dependencies": []}',
        )
        == []
    )
    assert registry.artifact_facts_from_text("pip-audit", path, "{not-json") == []


def test_pip_audit_fact_without_optional_details_keeps_base_message() -> None:
    """A minimal vulnerability does not gain dangling separators."""

    payload = {
        "dependencies": [
            {
                "name": "demo",
                "version": "1.0",
                "vulns": [{"id": "PYSEC-2026-2"}],
            }
        ]
    }

    facts = registry.artifact_facts_from_text(
        "pip-audit",
        Path(".verify-logs/pip-audit.json"),
        json.dumps(payload),
    )

    assert facts[0]["message"] == "demo 1.0: PYSEC-2026-2"
