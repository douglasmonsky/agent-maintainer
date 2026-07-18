"""Tests exact repair facts from OSV Scanner v2 JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts import registry

FIXTURE = Path(__file__).parents[1] / "fixtures" / "osv-scanner" / "v2-grouped.json"
INVALID_OSV_PAYLOADS: tuple[object, ...] = (
    None,
    list[object](),
    dict[str, object](),
    dict[str, object](results=dict[str, object]()),
    dict[str, object](
        results=list[object]((None, dict[str, object]())),
    ),
)
OSV_FACT_LIMIT = 500


def artifact_facts(payload: object) -> list[dict[str, object]]:
    """Parse one in-memory OSV payload through the public registry."""

    return registry.artifact_facts_from_text(
        "osv-scanner",
        Path(".verify-logs/osv-scanner.json"),
        json.dumps(payload),
    )


# docsync:evidence.start evidence.typescript.osv_fact_tests
def test_osv_v2_groups_emit_safe_deduplicated_facts() -> None:
    """Current grouped output retains fixes while redacting absolute paths."""

    facts = registry.artifact_facts("osv-scanner", FIXTURE)

    assert facts == [
        {
            "check": "osv-scanner",
            "path": "apps/web/package-lock.json",
            "line": None,
            "column": None,
            "symbol": "CVE-2021-23337",
            "message": (
                "npm/lodash 4.17.20: CVE-2021-23337 "
                "(GHSA-35jh-r3h4-6jhm); source: apps/web/package-lock.json; "
                "fix: 4.17.21; severity: HIGH; Command injection in lodash"
            ),
            "severity": "error",
        },
        {
            "check": "osv-scanner",
            "path": None,
            "line": None,
            "column": None,
            "symbol": "GHSA-demo",
            "message": ("npm/demo 1.0.0: GHSA-demo; source: pnpm-lock.yaml; A standalone advisory"),
            "severity": "error",
        },
    ]


def test_osv_nested_version_wins_with_legacy_outer_fallback() -> None:
    """V2 nested versions win while older captured output remains readable."""

    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "nested",
                            "version": "2",
                        },
                        "version": "1",
                        "vulnerabilities": [{"id": "OSV-NESTED"}],
                    },
                    {
                        "package": {"ecosystem": "npm", "name": "legacy"},
                        "version": "3",
                        "vulnerabilities": [{"id": "OSV-LEGACY"}],
                    },
                ],
            }
        ]
    }

    messages = [str(fact["message"]) for fact in artifact_facts(payload)]

    assert messages[0].startswith("npm/legacy 3: OSV-LEGACY")
    assert messages[1].startswith("npm/nested 2: OSV-NESTED")


@pytest.mark.parametrize(
    "payload",
    INVALID_OSV_PAYLOADS,
)
def test_osv_invalid_payloads_emit_no_facts(payload: object) -> None:
    """Invalid roots and empty malformed neighbors fail closed."""

    assert artifact_facts(payload) == []


def test_osv_malformed_group_does_not_hide_valid_vulnerability() -> None:
    """Ungrouped valid advisories survive malformed neighboring groups."""

    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "demo",
                            "version": "1",
                        },
                        "vulnerabilities": [{"id": "OSV-1"}, {"id": "OSV-2"}],
                        "groups": [{"ids": ["OSV-1"]}, {"ids": "bad"}],
                    }
                ],
            }
        ]
    }

    assert [fact["symbol"] for fact in artifact_facts(payload)] == [
        "OSV-1",
        "OSV-2",
    ]


def test_osv_unsafe_paths_never_enter_fact_paths_or_messages() -> None:
    """Absolute, drive-qualified, and traversal sources expose filenames only."""

    payload = {
        "results": [
            {
                "source": {"path": "../../private/package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "traversal",
                            "version": "1",
                        },
                        "vulnerabilities": [{"id": "OSV-TRAVERSAL"}],
                    }
                ],
            },
            {
                "source": {"path": "C:\\private\\pnpm-lock.yaml", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "windows",
                            "version": "1",
                        },
                        "vulnerabilities": [{"id": "OSV-WINDOWS"}],
                    }
                ],
            },
        ]
    }

    facts = artifact_facts(payload)
    serialized = json.dumps(facts)

    assert [fact["path"] for fact in facts] == [None, None]
    assert "../../" not in serialized
    assert "C:\\\\private" not in serialized
    assert "package-lock.json" in serialized
    assert "pnpm-lock.yaml" in serialized


def test_osv_sorts_before_the_retention_limit() -> None:
    """The first 500 sorted findings are retained regardless of input order."""

    vulnerabilities = [{"id": f"OSV-{index:03d}"} for index in range(OSV_FACT_LIMIT, -1, -1)]
    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "demo",
                            "version": "1",
                        },
                        "vulnerabilities": vulnerabilities,
                    }
                ],
            }
        ]
    }

    facts = artifact_facts(payload)

    assert len(facts) == OSV_FACT_LIMIT
    assert facts[0]["symbol"] == "OSV-000"
    assert facts[-1]["symbol"] == "OSV-499"


# docsync:evidence.end evidence.typescript.osv_fact_tests
