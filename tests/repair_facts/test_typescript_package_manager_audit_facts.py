"""Contract tests for normalized TypeScript package-manager audit facts."""

# docsync:evidence.start evidence.typescript.package_manager_audit_facts

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts.parsers import typescript_audit_adapter_utils as adapter_utils
from agent_repair_facts.parsers import typescript_package_manager_audit as audit
from agent_repair_facts.parsers import typescript_package_manager_audit_adapters as adapters
from agent_repair_facts.parsers.typescript_package_manager_audit_contract import RawAuditRecord

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "typescript_package_manager_audit"
EXPECTED_DUPLICATE_RECORDS = 2
EXPECTED_SECOND_VALUE = 2
SUMMARY_LINE_LIMIT = 5


def fixture_text(name: str) -> str:
    """Read one bounded synthetic manager projection."""

    return (FIXTURE_ROOT / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("manager", "fixture"),
    (("npm", "npm.json"), ("pnpm", "pnpm.json")),
)
def test_json_adapters_normalize_findings(manager: str, fixture: str) -> None:
    """Current npm and pnpm object reports share one normalized contract."""

    result = audit.parse_audit_report(manager, "root", manager, fixture_text(fixture))

    assert result.outcome == audit.AUDIT_OUTCOME_FINDINGS
    assert result.findings[0].manager == manager
    assert result.findings[0].package in {"kleur", "lodash", "minimist"}
    assert result.findings[0].advisory_ids
    assert result.findings[0].vulnerable_ranges


def test_npm_finding_preserves_directness_fix_and_safe_path() -> None:
    """npm fields remain explicit facts instead of inferred policy."""

    result = audit.parse_audit_report("npm", "root", "npm", fixture_text("npm.json"))
    finding = next(item for item in result.findings if item.package == "lodash")

    assert finding.severity == "high"
    assert finding.directness == "direct"
    assert finding.fixed_versions == ("4.17.21",)
    assert finding.path == "node_modules/lodash"
    assert finding.source_label == "node_modules/lodash"


def test_yarn_ndjson_keeps_valid_neighbors() -> None:
    """A malformed NDJSON neighbor cannot hide a valid Yarn advisory."""

    result = audit.parse_audit_report("yarn", "web", "yarn", fixture_text("yarn.ndjson"))

    assert result.outcome == audit.AUDIT_OUTCOME_FINDINGS
    assert result.supported_count == 1
    assert result.findings[0].workspace == "web"
    assert result.findings[0].advisory_ids == ("1234",)


def test_bun_ndjson_is_advisory_and_deterministic() -> None:
    """Bun records use the same sorted rendering as other managers."""

    result = audit.parse_audit_report("bun", "root", "bun", fixture_text("bun.ndjson"))

    assert result.outcome == audit.AUDIT_OUTCOME_FINDINGS
    assert [finding.package for finding in result.findings] == ["kleur", "lodash"]
    assert audit.render_audit_summary(result).splitlines()[0].startswith("bun/root: kleur")


def test_clean_and_invalid_outcomes_are_distinct() -> None:
    """Empty supported reports are clean while unsupported roots fail closed."""

    clean = audit.parse_audit_report(
        "npm",
        "root",
        "npm",
        '{"auditReportVersion":2,"vulnerabilities":{}}',
    )
    invalid = audit.parse_audit_report("npm", "root", "npm", '{"unexpected":true}')

    assert clean.outcome == audit.AUDIT_OUTCOME_CLEAN
    assert clean.findings == ()
    assert invalid.outcome == audit.AUDIT_OUTCOME_INVALID
    assert "invalid-input" in audit.render_audit_summary(invalid)


def test_malformed_ndjson_without_supported_records_is_invalid() -> None:
    """Malformed lines and records without explicit advisory IDs are invalid."""

    result = audit.parse_audit_report("bun", "root", "bun", fixture_text("malformed.ndjson"))

    assert result.outcome == audit.AUDIT_OUTCOME_INVALID
    assert result.supported_count == 0


def test_manager_is_never_inferred() -> None:
    """An unsupported manager cannot be selected from a recognizable report."""

    result = audit.parse_audit_report(
        "deno",
        "root",
        "deno",
        fixture_text("npm.json"),
    )

    assert result.outcome == audit.AUDIT_OUTCOME_INVALID
    assert result.findings == ()


def test_duplicate_advisories_merge_only_exact_equivalents() -> None:
    """Equivalent report records deduplicate without merging disagreeing ranges."""

    payload = {
        "advisories": {
            "GHSA-1234": {
                "module_name": "lodash",
                "severity": "high",
                "vulnerable_versions": "<4.17.21",
                "findings": [{"paths": ["node_modules/lodash"]}],
            },
            "GHSA-1234-copy": {
                "module_name": "lodash",
                "severity": "high",
                "vulnerable_versions": "<4.17.20",
                "findings": [{"paths": ["node_modules/lodash"]}],
            },
        }
    }

    result = audit.parse_audit_report("pnpm", "root", "pnpm", json.dumps(payload))

    assert result.supported_count == EXPECTED_DUPLICATE_RECORDS
    assert result.retained_count == EXPECTED_DUPLICATE_RECORDS
    assert {finding.vulnerable_ranges for finding in result.findings} == {
        ("<4.17.20",),
        ("<4.17.21",),
    }


def test_lists_scalars_and_findings_are_bounded_before_retention() -> None:
    """All list, scalar, and finding bounds are applied deterministically."""

    ids = [f"GHSA-{index:04d}" for index in range(30)]
    ranges = [f"<{index}.0.0" for index in range(30)]
    fixes = [f"{index}.0.1" for index in range(30)]
    payload = {
        "vulnerabilities": {
            "pkg": {
                "severity": "mystery",
                "via": ids,
                "range": ranges,
                "patched_versions": fixes,
            }
        }
    }
    many = {
        "vulnerabilities": {
            f"pkg-{index:03d}": {
                "severity": "low",
                "via": [f"GHSA-{index:04d}"],
            }
            for index in range(audit.AUDIT_FACT_LIMIT + 1)
        }
    }

    bounded = audit.parse_audit_report("npm", "root", "npm", json.dumps(payload))
    retained = audit.parse_audit_report("npm", "root", "npm", json.dumps(many))

    finding = bounded.findings[0]
    assert finding.severity == "unknown"
    assert len(finding.advisory_ids) == audit.AUDIT_LIST_LIMIT
    assert len(finding.vulnerable_ranges) == audit.AUDIT_LIST_LIMIT
    assert len(finding.fixed_versions) == audit.AUDIT_LIST_LIMIT
    assert retained.supported_count == audit.AUDIT_FACT_LIMIT + 1
    assert retained.retained_count == audit.AUDIT_FACT_LIMIT
    assert retained.findings[0].package == "pkg-000"


@pytest.mark.parametrize(
    ("reported_path", "expected_label"),
    (
        ("/private/source.ts", "source.ts"),
        ("../../private/source.ts", "source.ts"),
        ("C:\\private\\source.ts", "source.ts"),
        ("src/control\nsource.ts", "control source.ts"),
        ("src/spoof\u202esource.ts", "spoof source.ts"),
    ),
)
def test_unsafe_paths_are_display_only(reported_path: str, expected_label: str) -> None:
    """Absolute, traversing, drive, and control paths never become targets."""

    payload = {
        "vulnerabilities": {
            "pkg": {
                "severity": "high",
                "via": ["GHSA-1234"],
                "nodes": [reported_path],
            }
        }
    }

    finding = audit.parse_audit_report("npm", "root", "npm", json.dumps(payload)).findings[0]

    assert finding.path is None
    assert finding.source_label == expected_label


def test_summary_line_and_message_bounds_are_truthful() -> None:
    """Summary output honors line and character limits with an omission marker."""

    payload = {
        "advisories": {
            f"GHSA-{index:04d}": {
                "module_name": f"pkg-{index:03d}",
                "severity": "low",
                "vulnerable_versions": "<1.0.0",
            }
            for index in range(60)
        }
    }
    result = audit.parse_audit_report("pnpm", "root", "pnpm", json.dumps(payload))
    summary = audit.render_audit_summary(
        result,
        max_lines=SUMMARY_LINE_LIMIT,
        max_chars=1_000,
    )

    assert len(summary.splitlines()) <= SUMMARY_LINE_LIMIT
    assert "omitted" in summary
    assert len(summary) <= audit.AUDIT_MESSAGE_CHAR_LIMIT
    assert len(audit.format_audit_finding(result.findings[0])) <= audit.AUDIT_MESSAGE_CHAR_LIMIT


def test_adapter_helpers_fail_closed_and_preserve_explicit_fields() -> None:
    """Shared adapter helpers reject unsafe shapes without guessing."""

    record = {"id": "GHSA-1234", "package": "pkg", "severity": "high"}
    records = adapter_utils.records_from_items([record])
    assert records
    assert records[0].package == "pkg"
    assert adapter_utils.record_from_item("not an object") is None
    assert adapter_utils.record_from_vulnerability("pkg", "not an object") is None
    assert adapter_utils.record_from_vulnerability("pkg", {}) is None
    assert adapter_utils.vulnerability_map("not a map") is None
    assert adapter_utils.vulnerability_map(None) == ()
    advisory_records = adapter_utils.advisory_container([record])
    assert advisory_records
    assert advisory_records[0].advisory_ids == ("GHSA-1234",)
    assert adapter_utils.advisory_container("not a container") is None
    assert adapter_utils.advisory_container(None) == ()
    assert adapter_utils.scope({"scope": "runtime"}) == "runtime"
    assert adapter_utils.scope({"dev": True}) == "dev"
    assert adapter_utils.scope({"optional": True}) == "optional"
    assert adapter_utils.scope({"peer": True}) == "peer"
    assert adapter_utils.directness({"directness": "direct"}) == "direct"
    assert adapter_utils.directness({"isDirect": True}) == "direct"
    assert adapter_utils.directness({"isDirect": False}) == "indirect"
    assert adapter_utils.values(None) == ()
    assert adapter_utils.values(("one",)) == ("one",)
    assert (
        adapter_utils.first({"first": None, "second": EXPECTED_SECOND_VALUE}, "first", "second")
        == EXPECTED_SECOND_VALUE
    )
    assert adapter_utils.object_value({1: "unsafe"}) is None


def test_manager_adapters_cover_supported_projection_shapes() -> None:
    """Manager adapters keep list, summary, advisory, and data shapes bounded."""

    record = {"id": "GHSA-1234", "package": "pkg", "severity": "high"}
    npm_records = adapters.parse_npm_payload([record])
    assert npm_records
    assert npm_records[0].package == "pkg"
    assert adapters.parse_npm_payload("not JSON") is None
    assert adapters.parse_yarn_record("not JSON") is None
    assert adapters.parse_yarn_record({"type": "auditSummary"}) == ()
    yarn_records = adapters.parse_yarn_record(
        {"type": "auditAdvisory", "data": {"advisory": record}}
    )
    assert yarn_records
    assert yarn_records[0].package == "pkg"
    assert adapters.parse_yarn_record({"type": "auditAdvisory", "data": {"advisory": {}}}) is None
    assert adapters.parse_bun_payload("not JSON") is None
    assert adapters.parse_bun_payload({"type": "auditSummary"}) == ()
    bun_data_records = adapters.parse_bun_payload({"data": {"advisory": record}})
    assert bun_data_records
    assert bun_data_records[0].package == "pkg"
    bun_records = adapters.parse_bun_payload(record)
    assert bun_records
    assert bun_records[0].package == "pkg"


def test_parser_edge_outcomes_and_bounded_rendering() -> None:
    """Empty, omitted, scalar, and invalid raw fields remain deterministic."""

    assert audit.parse_audit_report("npm", "root", "npm", "").outcome == audit.AUDIT_OUTCOME_INVALID
    clean = audit.parse_audit_report(
        "npm", "root", "npm", '{"auditReportVersion":2,"vulnerabilities":{}}'
    )
    assert audit.render_audit_summary(clean) == "npm: no audit findings"
    private_names = ("_bounded_values", "_scalar", "_normalize_record", "_truncate")
    bounded_values, scalar, normalize_record, truncate = (
        getattr(audit, name) for name in private_names
    )
    assert bounded_values("GHSA-1") == ("GHSA-1",)
    assert bounded_values(1) == ("1",)
    assert bounded_values({"value": 1}) == ()
    assert scalar(True) == ""
    assert scalar({"value": 1}) == ""
    assert (
        normalize_record(
            "npm",
            "root",
            "npm",
            RawAuditRecord(package="", severity="high", advisory_ids=("ADV-1",)),
        )
        is None
    )
    finding = audit.PackageManagerAuditFinding(
        manager="npm",
        package="pkg",
        severity="high",
        advisory_ids=("ADV-1",),
        vulnerable_ranges=("<1",),
        fixed_versions=("1.0.0",),
        scope="dev",
        directness="direct",
        workspace="root",
        path=None,
        source_label="<unknown source>",
        title="upgrade pkg",
    )
    result = audit.PackageManagerAuditParseResult(
        manager="npm",
        workspace="root",
        outcome=audit.AUDIT_OUTCOME_FINDINGS,
        findings=(finding,),
        supported_count=3,
        retained_count=1,
        omitted_count=2,
    )
    assert "audit findings omitted" in audit.render_audit_summary(result)
    assert "upgrade pkg" in audit.format_audit_finding(finding)
    assert truncate("abcdef", 3) == "abc"
    assert truncate("abcdef", 5) == "ab..."


# docsync:evidence.end evidence.typescript.package_manager_audit_facts
