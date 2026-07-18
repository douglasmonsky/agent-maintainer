"""Tests exact repair facts from OSV Scanner v2 JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts import registry
from agent_repair_facts.parsers import osv_scanner

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


def test_osv_partial_group_preserves_canonical_and_missing_alias() -> None:
    """Valid group IDs survive when only one embedded advisory is available."""

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
                        "vulnerabilities": [{"id": "GHSA-1", "summary": "partial artifact"}],
                        "groups": [{"ids": ["GHSA-1", "CVE-1"]}],
                    }
                ],
            }
        ]
    }

    facts = artifact_facts(payload)

    assert len(facts) == 1
    assert facts[0]["symbol"] == "CVE-1"
    assert "CVE-1 (GHSA-1)" in str(facts[0]["message"])
    assert "partial artifact" in str(facts[0]["message"])


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


@pytest.mark.parametrize("source_path", ("..", "../..", "C:\\", "\n"))
def test_osv_unsafe_source_without_filename_uses_unknown_label(source_path: str) -> None:
    """Traversal identities, drive roots, and controls have no display filename."""

    payload = {
        "results": [
            {
                "source": {"path": source_path, "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "demo",
                            "version": "1",
                        },
                        "vulnerabilities": [{"id": "OSV-1"}],
                    }
                ],
            }
        ]
    }

    fact = artifact_facts(payload)[0]

    assert fact["path"] is None
    assert "source: <unknown source>" in str(fact["message"])


def test_osv_overlong_source_is_nontargetable_with_safe_filename() -> None:
    """An oversized relative path retains only its independently safe filename."""

    source_path = f"packages/{'x' * 501}/package-lock.json"
    payload = {
        "results": [
            {
                "source": {"path": source_path, "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "demo",
                            "version": "1",
                        },
                        "vulnerabilities": [{"id": "OSV-1"}],
                    }
                ],
            }
        ]
    }

    fact = artifact_facts(payload)[0]

    assert fact["path"] is None
    assert "source: package-lock.json" in str(fact["message"])


def test_osv_rendered_fields_are_single_line_and_bounded() -> None:
    """Control characters and oversized advisory lists cannot expand context."""

    aliases = [f"GHSA-{index:03d}-" + ("x" * 300) for index in range(100)]
    fixes = [{"fixed": f"{index}.0." + ("x" * 300)} for index in range(100)]
    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lock\nfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm\nINJECTED",
                            "name": "demo\nINJECTED" + ("x" * 500),
                            "version": "1\nINJECTED",
                        },
                        "vulnerabilities": [
                            {
                                "id": "OSV-1\nINJECTED",
                                "aliases": aliases,
                                "summary": "summary\nINJECTED " + ("x" * 500),
                                "affected": [{"ranges": [{"events": fixes}]}],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    parsed = osv_scanner.parse_osv_payload(payload)
    message = osv_scanner.format_osv_finding(parsed.findings[0])

    assert "\n" not in message
    assert len(message) <= osv_scanner.OSV_MESSAGE_CHAR_LIMIT
    assert len(parsed.findings[0].aliases) <= osv_scanner.OSV_LIST_ITEM_LIMIT
    assert len(parsed.findings[0].fixed_versions) <= osv_scanner.OSV_LIST_ITEM_LIMIT


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
