"""Contract tests for sanitized Java/Gradle provider calibration evidence."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import cast

import pytest

from agent_maintainer.core.setup_plans import render_reviewed_diff
from agent_maintainer.ecosystems.java.reports.jacoco import parse_jacoco_report
from agent_maintainer.ecosystems.java.setup import plan_java_setup
from tests.support.paths import REPO_ROOT

CALIBRATION_ROOT = REPO_ROOT / "tests" / "fixtures" / "java_gradle" / "calibration"
CASE_STUDY = REPO_ROOT / "docs" / "case-studies" / "java-gradle-provider-calibration.md"
EXPECTED_CASES = {
    "java-only": "tests/fixtures/java_gradle/groovy_single",
    "mixed-python-java": "tests/fixtures/java_gradle/mixed_python_java",
    "multi-project": "tests/fixtures/java_gradle/kotlin_multi",
}
MAX_FALSE_POSITIVES = 1
MAX_CALIBRATION_SECONDS = 120


@pytest.fixture(scope="module")
def evidence_by_case() -> dict[str, dict[str, object]]:
    evidence = {}
    for path in sorted(CALIBRATION_ROOT.glob("*.json")):
        payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        evidence[cast(str, payload["case_id"])] = payload
    return evidence


def test_calibration_has_exact_required_sanitized_cases(
    evidence_by_case: dict[str, dict[str, object]],
) -> None:
    assert set(evidence_by_case) == set(EXPECTED_CASES)
    for case_id, fixture in EXPECTED_CASES.items():
        evidence = evidence_by_case[case_id]
        assert evidence["schema_version"] == 1
        assert evidence["fixture"] == fixture
        assert evidence["sanitized"] is True
        assert evidence["external_repository_claim"] is False
        assert (REPO_ROOT / fixture).is_dir()


def test_setup_measurements_match_current_reviewed_plans(
    evidence_by_case: dict[str, dict[str, object]],
) -> None:
    for evidence in evidence_by_case.values():
        fixture = REPO_ROOT / cast(str, evidence["fixture"])
        setup = cast(dict[str, object], evidence["setup"])
        plan = plan_java_setup(fixture)
        assert setup["status"] == plan.status.value
        assert setup["changed_files"] == len(plan.edits)
        assert setup["manual_edits"] == int(plan.semantic_edit is not None)
        assert setup["diff_lines"] == len(render_reviewed_diff(plan.edits).splitlines())
        assert setup["restructures_build"] is False


def test_runtime_noise_repair_and_baseline_measurements_are_bounded(
    evidence_by_case: dict[str, dict[str, object]],
) -> None:
    for evidence in evidence_by_case.values():
        verification = cast(dict[str, object], evidence["verification"])
        repair = cast(dict[str, object], evidence["repair_facts"])
        churn = cast(dict[str, object], evidence["baseline_churn"])
        assert verification["wrapper_calls"] == 1
        assert 0 < cast(int, verification["runtime_seconds"]) <= MAX_CALIBRATION_SECONDS
        assert 0 <= cast(int, evidence["false_positives"]) <= MAX_FALSE_POSITIVES
        assert repair["seeded_failures"] == repair["actionable_facts"]
        assert repair["useful"] is True
        assert cast(int, churn["initial_entries"]) >= 0
        assert cast(int, churn["entries_changed_on_noop"]) == 0
        assert cast(int, churn["pruned_entries"]) >= 0
        assert churn["silent_threshold_lowering"] is False


def test_coverage_facts_match_real_sanitized_reports_without_synthetic_aggregation(
    evidence_by_case: dict[str, dict[str, object]],
) -> None:
    for case_id, evidence in evidence_by_case.items():
        facts = cast(list[dict[str, object]], evidence["coverage"])
        labels = []
        for fact in facts:
            report_path = REPO_ROOT / cast(str, evidence["fixture"]) / cast(str, fact["report"])
            coverage = parse_jacoco_report(report_path)
            assert fact["line_percentage"] == str(coverage.line.percentage)
            assert fact["branch_percentage"] == str(coverage.branch.percentage)
            labels.append(cast(str, fact["label"]))
        assert len(labels) == len(set(labels))
        if case_id == "multi-project":
            assert set(labels) == {":", ":app"}
            assert {fact["scope"] for fact in facts} == {"project"}
        else:
            assert labels == [":"]


def test_new_defaults_and_established_ratchets_are_calibrated_separately(
    evidence_by_case: dict[str, dict[str, object]],
) -> None:
    for evidence in evidence_by_case.values():
        thresholds = cast(dict[str, object], evidence["thresholds"])
        assert thresholds["mode"] in {"new-repository", "established-ratchet"}
        current_line = Decimal(cast(str, thresholds["current_line"]))
        current_branch = Decimal(cast(str, thresholds["current_branch"]))
        if thresholds["mode"] == "new-repository":
            assert (current_line, current_branch) == (Decimal("0.80"), Decimal("0.70"))
            assert thresholds["base_line"] is None
            assert thresholds["base_branch"] is None
        else:
            assert current_line >= Decimal(cast(str, thresholds["base_line"]))
            assert current_branch >= Decimal(cast(str, thresholds["base_branch"]))


def test_case_study_reports_scope_results_and_limitations(
    evidence_by_case: dict[str, dict[str, object]],
) -> None:
    text = CASE_STUDY.read_text(encoding="utf-8")
    normalized = " ".join(text.lower().split())
    for case_id in evidence_by_case:
        assert f"`{case_id}`" in text
    assert "sanitized" in normalized
    assert "wrapper calls" in normalized
    assert "false positives" in normalized
    assert "baseline churn" in normalized
    assert "does not promote" in normalized
