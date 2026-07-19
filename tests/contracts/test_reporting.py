"""Deterministic contract report rendering tests."""

from __future__ import annotations

import json
from typing import cast

from agent_maintainer.contracts.limits import MAX_REPORT_ITEMS
from agent_maintainer.contracts.models import (
    ContractChange,
    ContractDecision,
    ContractObligation,
    ContractReport,
    Descriptor,
    RepairFact,
)
from agent_maintainer.contracts.reporting import render_json, render_text, report_to_dict


def _descriptor(contract_id: str) -> Descriptor:
    return Descriptor(
        contract_id=contract_id,
        kind="python-api",
        owner="agent_maintainer.api",
        stability="beta",
        revision=2,
        sources=(f"src/{contract_id}.py",),
        body={"exports": [{"kind": "function", "name": "run"}]},
        fingerprint=f"sha256:{'a' if contract_id == 'a-api' else 'b'}" + "0" * 63,
    )


def _change(contract_id: str, fingerprint: str) -> ContractChange:
    return ContractChange(
        contract_id=contract_id,
        operation="member-remove",
        path="/exports/run",
        before={"name": "run"},
        after=None,
        classification="breaking",
        fingerprint=fingerprint,
        reason="public member was removed",
    )


def sample_report() -> ContractReport:
    """Return intentionally unsorted report facts."""
    first_fingerprint = "sha256:" + "1" * 64
    second_fingerprint = "sha256:" + "2" * 64
    return ContractReport(
        mode="check",
        base_ref="origin/main",
        base_available=True,
        base_package_version="0.1.0b9",
        current_package_version="0.1.0b10",
        descriptors=(_descriptor("z-api"), _descriptor("a-api")),
        changes=(
            _change("z-api", second_fingerprint),
            _change("a-api", first_fingerprint),
        ),
        obligations=(
            ContractObligation(
                kind="package-version",
                status="satisfied",
                message="package version satisfies the minimum recommendation",
                minimum_impact="prerelease",
                current="0.1.0b10",
                expected="0.1.0b10",
            ),
            ContractObligation(
                kind="contract-revision",
                status="unresolved",
                message="contract revision does not match semantic drift",
                contract_id="a-api",
                current="1",
                expected="2",
                fingerprints=(first_fingerprint,),
            ),
        ),
        decisions=(
            ContractDecision(
                contract="z-api",
                fingerprint=second_fingerprint,
                classification="breaking",
                reason="Reviewed removal.",
            ),
            ContractDecision(
                contract="a-api",
                fingerprint=first_fingerprint,
                classification="compatible",
                reason="Alias remains.",
            ),
        ),
        repair_facts=(
            RepairFact(
                contract_id="z-api",
                fingerprint=second_fingerprint,
                summary="add migration evidence",
                inspect_command="agent-maintainer contract diff --base-ref origin/main --json",
            ),
            RepairFact(
                contract_id="a-api",
                fingerprint=first_fingerprint,
                summary="advance revision",
                inspect_command="agent-maintainer contract diff --base-ref origin/main --json",
            ),
        ),
        advisories=("second", "first"),
        can_snapshot=False,
    )


def _object_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload[key]
    assert isinstance(value, list)
    items = cast(list[object], value)
    assert all(isinstance(item, dict) for item in items)
    return cast(list[dict[str, object]], items)


def test_report_dictionary_has_explicit_schema_and_sorted_facts() -> None:
    """Serialization is intentional and independent of dataclass field mechanics."""
    payload = report_to_dict(sample_report())

    assert tuple(payload) == (
        "schema_version",
        "mode",
        "base_ref",
        "base_available",
        "base_package_version",
        "current_package_version",
        "can_snapshot",
        "unresolved",
        "descriptors",
        "changes",
        "obligations",
        "decisions",
        "repair_facts",
        "advisories",
        "errors",
    )
    assert [item["contract_id"] for item in _object_list(payload, "descriptors")] == [
        "a-api",
        "z-api",
    ]
    assert [item["contract_id"] for item in _object_list(payload, "changes")] == [
        "a-api",
        "z-api",
    ]
    assert [item["contract"] for item in _object_list(payload, "decisions")] == [
        "a-api",
        "z-api",
    ]
    assert [item["contract_id"] for item in _object_list(payload, "repair_facts")] == [
        "a-api",
        "z-api",
    ]


def test_json_report_is_byte_stable_and_complete() -> None:
    """JSON contains every exact fact with one stable trailing newline."""
    first = render_json(sample_report())
    second = render_json(sample_report())
    payload = json.loads(first)

    assert first == second
    assert first.endswith("\n")
    assert not first.endswith("\n\n")
    assert payload["schema_version"] == 1
    assert "timestamp" not in first
    assert payload["changes"][0]["fingerprint"].startswith("sha256:")
    assert payload["repair_facts"][0]["fingerprint"].startswith("sha256:")


def test_renderers_ascii_escape_control_and_non_ascii_text() -> None:
    """Terminal and captured-log output cannot contain raw control text."""
    report = ContractReport(
        mode="diff",
        advisories=("caf\N{LATIN SMALL LETTER E WITH ACUTE}\nnext\tvalue",),
    )

    json_output = render_json(report)
    text_output = render_text(report)

    assert "caf\\u00e9\\nnext\\tvalue" in json_output
    assert "caf\\u00e9\\nnext\\tvalue" in text_output
    assert "caf\N{LATIN SMALL LETTER E WITH ACUTE}" not in text_output


def test_human_sections_are_bounded_and_point_to_json() -> None:
    """Human output caps every repeated section without dropping JSON facts."""
    advisories = tuple(f"advisory-{index:03d}" for index in range(MAX_REPORT_ITEMS + 3))
    report = ContractReport(mode="diff", advisories=advisories)

    output = render_text(report)

    assert "advisory-000" in output
    assert f"advisory-{MAX_REPORT_ITEMS - 1:03d}" in output
    assert f"advisory-{MAX_REPORT_ITEMS:03d}" not in output
    assert "3 more; use --json" in output
    assert len(json.loads(render_json(report))["advisories"]) == MAX_REPORT_ITEMS + 3


def test_renderers_do_not_invent_absolute_paths_or_timestamps() -> None:
    """Repository-relative model facts stay repository-relative in both formats."""
    report = sample_report()

    for output in (render_json(report), render_text(report)):
        assert "/Users/" not in output
        assert "/private/" not in output
        assert "created_at" not in output
