"""Tests exact repair facts from dependency-cruiser JSON output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_repair_facts import registry
from agent_repair_facts.parsers import typescript_dependency_cruiser

FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "typescript_dependency_cruiser"
    / "supported-violations.json"
)
FACT_LIMIT = 500
FIELD_LIMIT = 200
MESSAGE_LIMIT = 1_000
SUPPORTED_TYPES = {
    "cycle",
    "dependency",
    "folder",
    "instability",
    "module",
    "reachability",
}


def facts_from(
    payload: object,
    check: str = "typescript-dependency-cruiser",
) -> list[dict[str, object]]:
    """Parse one in-memory dependency-cruiser payload through the registry."""

    return registry.log_facts_from_text(
        check,
        Path("typescript-dependency-cruiser.log"),
        json.dumps(payload),
    )


def violation(
    source: object = "src/source.ts",
    target: object = "src/target.ts",
    *,
    rule: object = "boundary-rule",
    severity: object = "error",
    violation_type: object = "dependency",
) -> dict[str, object]:
    """Build one dependency-cruiser summary violation."""

    return {
        "from": source,
        "to": target,
        "type": violation_type,
        "rule": {"name": rule, "severity": severity},
    }


def payload(*violations: object) -> dict[str, object]:
    """Build the supported cruise-result envelope."""

    return {"summary": {"violations": list(violations)}, "modules": []}


# docsync:evidence.start evidence.typescript.dependency_cruiser_fact_tests
def test_fixture_emits_sorted_safe_facts_for_workspace_check() -> None:
    """The public registry preserves workspace names and normalized details."""

    facts = registry.log_facts(
        "typescript-dependency-cruiser:web",
        FIXTURE,
    )

    assert facts[0] == {
        "check": "typescript-dependency-cruiser:web",
        "path": "src/api/client.ts",
        "line": None,
        "column": None,
        "symbol": "api-not-to-db",
        "message": (
            "src/api/client.ts -> src/db/private.ts: "
            "api-not-to-db [error; dependency]"
        ),
        "severity": "error",
    }
    observed_types = {
        str(fact["message"]).rsplit("; ", 1)[-1].removesuffix("]")
        for fact in facts
    }
    assert observed_types >= SUPPORTED_TYPES
    assert all(fact["check"] == "typescript-dependency-cruiser:web" for fact in facts)


@pytest.mark.parametrize(
    "raw_output",
    (
        "{not-json",
        "null",
        "[]",
        "{}",
        '{"summary": []}',
        '{"summary": {}}',
        '{"summary": {"violations": {}}}',
    ),
)
def test_invalid_envelopes_fail_closed(raw_output: str) -> None:
    """Malformed JSON and unsupported root shapes emit no structured facts."""

    result = typescript_dependency_cruiser.parse_dependency_cruiser_json_result(
        raw_output,
    )

    assert result.valid is False
    assert result.findings == ()
    assert result.supported_count == 0


def test_malformed_neighbors_do_not_hide_valid_violation() -> None:
    """Each summary violation is validated independently."""

    malformed_rule = violation(rule="boundary-rule")
    malformed_rule["rule"] = "bad"

    facts = facts_from(
        payload(
            None,
            [],
            {"from": "src/incomplete.ts"},
            malformed_rule,
            violation(),
        )
    )

    assert [fact["symbol"] for fact in facts] == ["boundary-rule"]


@pytest.mark.parametrize("severity", ("error", "warn", "info"))
@pytest.mark.parametrize("violation_type", sorted(SUPPORTED_TYPES))
def test_supported_severities_and_types_are_preserved(
    severity: str,
    violation_type: str,
) -> None:
    """Documented dependency-cruiser values survive normalization."""

    fact = facts_from(
        payload(violation(severity=severity, violation_type=violation_type))
    )[0]

    assert fact["severity"] == severity
    assert str(fact["message"]).endswith(f"[{severity}; {violation_type}]")


@pytest.mark.parametrize("severity", ("ignore", "fatal", "", None, 2))
def test_unsupported_severities_are_skipped(severity: object) -> None:
    """Ignore and unknown severities remain non-actionable."""

    assert facts_from(payload(violation(severity=severity))) == []


def test_missing_type_is_supported_but_unknown_type_is_skipped() -> None:
    """The optional schema field may be absent but not silently reclassified."""

    without_type = violation()
    without_type.pop("type")

    facts = facts_from(payload(without_type, violation(violation_type="graph")))

    assert len(facts) == 1
    assert str(facts[0]["message"]).endswith("[error]")


@pytest.mark.parametrize("violation_type", ("", 2, [], {}))
def test_malformed_types_are_skipped(violation_type: object) -> None:
    """Malformed optional-type values are not mistaken for omission."""

    assert (
        facts_from(payload(violation(violation_type=violation_type))) == []
    )


def test_unresolved_target_is_used_only_when_to_is_unusable() -> None:
    """unresolvedTo supplies a display label without becoming a fact path."""

    raw = violation(target="")
    raw["unresolvedTo"] = "@scope/missing"

    fact = facts_from(payload(raw))[0]

    assert fact["path"] == "src/source.ts"
    assert "src/source.ts -> @scope/missing" in str(fact["message"])


def test_findings_sort_before_the_retention_limit() -> None:
    """The retained 500 facts are deterministic regardless of input order."""

    violations = [
        violation(source=f"src/{index:03d}.ts", rule=f"rule-{index:03d}")
        for index in range(FACT_LIMIT, -1, -1)
    ]

    result = typescript_dependency_cruiser.parse_dependency_cruiser_json_result(
        json.dumps(payload(*violations))
    )

    assert result.valid is True
    assert result.supported_count == FACT_LIMIT + 1
    assert len(result.findings) == FACT_LIMIT
    assert result.findings[0].source_label == "src/000.ts"
    assert result.findings[-1].source_label == "src/499.ts"


@pytest.mark.parametrize(
    ("source", "display"),
    (
        ("/private/source.ts", "source.ts"),
        ("../../private/source.ts", "source.ts"),
        ("C:\\private\\source.ts", "source.ts"),
        ("src/control\nsource.ts", "control source.ts"),
    ),
)
def test_unsafe_sources_are_display_only(source: str, display: str) -> None:
    """Unsafe paths never enter context targets or leak unsafe prefixes."""

    fact = facts_from(payload(violation(source=source)))[0]

    assert fact["path"] is None
    assert str(fact["message"]).startswith(f"{display} -> src/target.ts")


def test_empty_source_is_skipped() -> None:
    """A source identity is required for an actionable violation."""

    assert facts_from(payload(violation(source=""))) == []


@pytest.mark.parametrize("source", (".", "..", "../.."))
def test_source_without_safe_identity_is_skipped(source: str) -> None:
    """A rejected path with no safe basename cannot identify a finding."""

    assert facts_from(payload(violation(source=source))) == []


def test_overlong_relative_source_is_nontargetable_with_safe_display() -> None:
    """The path cap is checked before bounded display normalization."""

    source = f"packages/{'x' * 501}/source.ts"
    fact = facts_from(payload(violation(source=source)))[0]

    assert fact["path"] is None
    assert str(fact["message"]).startswith("source.ts -> src/target.ts")


def test_scalars_and_messages_are_single_line_and_bounded() -> None:
    """Untrusted scalar content cannot expand context output."""

    finding = violation(
        source="src/source.ts",
        target="src/" + ("target" * 100) + ".ts",
        rule="rule\nINJECTED " + ("x" * 2_000),
    )
    result = typescript_dependency_cruiser.parse_dependency_cruiser_json_result(
        json.dumps(payload(finding))
    )
    parsed = result.findings[0]
    message = typescript_dependency_cruiser.format_dependency_cruiser_finding(parsed)

    assert len(parsed.source_label) <= FIELD_LIMIT
    assert len(parsed.target_label) <= FIELD_LIMIT
    assert len(parsed.rule) <= FIELD_LIMIT
    assert "\n" not in message
    assert len(message) <= MESSAGE_LIMIT


# docsync:evidence.end evidence.typescript.dependency_cruiser_fact_tests
