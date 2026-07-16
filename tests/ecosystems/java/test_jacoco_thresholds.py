"""Tests upward-only JaCoCo threshold policy and exact headroom."""

from __future__ import annotations

import subprocess  # nosec B404 - isolated local Git fixture
from decimal import Decimal
from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java import jacoco_thresholds
from agent_maintainer.ecosystems.java.reports.jacoco import JacocoCounter, JacocoCoverage

LINE_PROPERTY = "agentMaintainer.jacoco.minimumLineCoverage"
BRANCH_PROPERTY = "agentMaintainer.jacoco.minimumBranchCoverage"
PROPERTY_NAMES = jacoco_thresholds.JacocoPropertyNames(LINE_PROPERTY, BRANCH_PROPERTY)

# docsync:evidence.start evidence.java.coverage_rollout_tests


def test_new_repository_defaults_and_established_floors_are_distinct() -> None:
    observed = JacocoCoverage(
        line=JacocoCounter(missed=160001, covered=839999),
        branch=JacocoCounter(missed=270001, covered=729999),
    )

    assert jacoco_thresholds.default_thresholds() == jacoco_thresholds.JacocoThresholds(
        line=Decimal("0.80"),
        branch=Decimal("0.70"),
    )
    assert jacoco_thresholds.established_thresholds(observed) == (
        jacoco_thresholds.JacocoThresholds(
            line=Decimal("0.83"),
            branch=Decimal("0.72"),
        )
    )


def test_base_ref_thresholds_may_stay_equal_or_rise_and_headroom_is_separate(
    tmp_path: Path,
) -> None:
    repo = initialized_repo(tmp_path, line="0.80", branch="0.70")
    write_properties(repo, line="0.81", branch="0.70")
    coverage = JacocoCoverage(
        line=JacocoCounter(missed=15, covered=85),
        branch=JacocoCounter(missed=35, covered=65),
    )

    report = jacoco_thresholds.evaluate_thresholds(
        repo,
        gradle_root=Path("."),
        base_ref="HEAD",
        properties=PROPERTY_NAMES,
        coverage=coverage,
    )

    assert report.passed is True
    assert report.current.line == Decimal("0.81")
    assert report.base.line == Decimal("0.80")
    assert report.line_headroom == Decimal("4.0000")
    assert report.branch_headroom == Decimal("-5.0000")


def test_downward_property_change_is_a_regression(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path, line="0.80", branch="0.70")
    write_properties(repo, line="0.79", branch="0.71")
    coverage = JacocoCoverage(
        line=JacocoCounter(missed=10, covered=90),
        branch=JacocoCounter(missed=20, covered=80),
    )

    report = jacoco_thresholds.evaluate_thresholds(
        repo,
        gradle_root=Path("."),
        base_ref="HEAD",
        properties=PROPERTY_NAMES,
        coverage=coverage,
    )

    assert report.passed is False
    assert report.regressions == ("line",)


@pytest.mark.parametrize(
    ("base_ref", "base_payload"),
    (
        ("missing-ref", "0.80|0.70"),
        ("HEAD", "missing|0.70"),
    ),
)
def test_required_base_data_must_be_available(
    tmp_path: Path,
    base_ref: str,
    base_payload: str,
) -> None:
    base_line, base_branch = base_payload.split("|")
    repo = initialized_repo(tmp_path, line=base_line, branch=base_branch)
    write_properties(repo, line="0.80", branch="0.70")
    coverage = JacocoCoverage(
        line=JacocoCounter(missed=20, covered=80),
        branch=JacocoCounter(missed=30, covered=70),
    )

    with pytest.raises(jacoco_thresholds.JacocoThresholdError):
        jacoco_thresholds.evaluate_thresholds(
            repo,
            gradle_root=Path("."),
            base_ref=base_ref,
            properties=PROPERTY_NAMES,
            coverage=coverage,
        )


@pytest.mark.parametrize("value", ("", "1.01", "-0.1", "eighty", "0.80000"))
def test_invalid_property_values_fail_closed(tmp_path: Path, value: str) -> None:
    repo = initialized_repo(tmp_path, line="0.80", branch="0.70")
    write_properties(repo, line=value, branch="0.70")

    with pytest.raises(jacoco_thresholds.JacocoThresholdError):
        jacoco_thresholds.read_current_thresholds(
            repo,
            gradle_root=Path("."),
            properties=PROPERTY_NAMES,
        )


def initialized_repo(tmp_path: Path, *, line: str, branch: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "tests@example.com")
    git(repo, "config", "user.name", "Tests")
    write_properties(repo, line=line, branch=branch)
    git(repo, "add", "gradle.properties")
    git(repo, "commit", "-qm", "base thresholds")
    return repo


def write_properties(repo: Path, *, line: str, branch: str) -> None:
    values = []
    if line != "missing":
        values.append(f"{LINE_PROPERTY}={line}")
    if branch != "missing":
        values.append(f"{BRANCH_PROPERTY}={branch}")
    (repo / "gradle.properties").write_text(f"{'\n'.join(values)}\n", encoding="utf-8")


def git(repo: Path, *args: str) -> None:
    subprocess.run(("git", "-C", str(repo), *args), check=True, capture_output=True)  # nosec B603


# docsync:evidence.end evidence.java.coverage_rollout_tests
