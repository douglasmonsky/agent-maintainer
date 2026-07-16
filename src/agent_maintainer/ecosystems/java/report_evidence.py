"""Task-scoped report freshness, parsing, and Java debt comparison."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent_maintainer.ecosystems.java import baseline, provider
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.java.findings import JavaFinding
from agent_maintainer.ecosystems.java.observations import GradleObservation, ReportSnapshot
from agent_maintainer.ecosystems.java.report_outcomes import (
    JavaReportEvidenceError,
    validate_report_outcomes,
)
from agent_maintainer.ecosystems.java.reports import checkstyle, jacoco, junit, pmd, spotbugs

MAX_ARTIFACT_FINDINGS = 12
MAX_ARTIFACT_PROBLEMS = 6
MAX_ARTIFACT_FACT_TEXT = 256
MAX_ARTIFACT_PATH_TEXT = 512
SUPPORTED_STATIC_TOOLS = frozenset(("checkstyle", "pmd", "spotbugs"))


@dataclass(frozen=True)
class JavaReportEvidence:
    """Bounded parsed reports and comparison outcome."""

    report_counts: tuple[tuple[str, int], ...]
    findings: tuple[JavaFinding, ...]
    tests: junit.JUnitReport | None
    coverage: tuple[JacocoCoverageFact, ...]
    debt: baseline.FindingDebtReport | None
    baseline_present: bool

    @property
    def passed(self) -> bool:
        """Return whether reports contain no test or debt regression."""
        tests_passed = self.tests is None or (self.tests.failures == 0 and self.tests.errors == 0)
        debt_passed = self.debt is None or self.debt.passed
        return tests_passed and debt_passed

    @property
    def report_count(self) -> int:
        """Return the number of parsed XML reports."""
        return sum(count for _, count in self.report_counts)

    def spotbugs_payload(self) -> dict[str, int] | None:
        """Return the existing native-ratchet summary when SpotBugs ran."""
        count = dict(self.report_counts).get("spotbugs", 0)
        if count == 0:
            return None
        findings = sum(finding.tool == "spotbugs" for finding in self.findings)
        return {"reports": count, "findings": findings}

    def to_payload(self) -> dict[str, object]:
        """Return sanitized bounded report facts for the run artifact."""
        finding_facts = tuple(_finding_payload(item) for item in self.findings)
        payload: dict[str, object] = {
            "report_count": self.report_count,
            "tools": dict(self.report_counts),
            "finding_count": len(self.findings),
            "findings": finding_facts[:MAX_ARTIFACT_FINDINGS],
            "findings_truncated": len(finding_facts) > MAX_ARTIFACT_FINDINGS,
        }
        if self.tests is not None:
            payload["tests"] = _tests_payload(self.tests)
        if self.coverage:
            payload["coverage"] = tuple(_coverage_payload(item) for item in self.coverage)
        if self.debt is not None:
            payload["baseline"] = _debt_payload(self.debt, self.baseline_present)
        return payload


def collect_report_evidence(
    workspace: Path,
    gradle_root: Path,
    plans: tuple[provider.JavaReportPlan, ...],
    observation: GradleObservation,
    findings_baseline: str,
) -> JavaReportEvidence:
    """Validate, parse, and compare every task-scoped report exactly once."""
    snapshots = validate_report_outcomes(gradle_root, plans, observation)
    parsed = _parse_reports(gradle_root, snapshots)
    selected_tools = frozenset(item.tool for item in snapshots) & SUPPORTED_STATIC_TOOLS
    debt, baseline_present = _compare_findings(
        workspace,
        findings_baseline,
        parsed.findings,
        selected_tools,
    )
    report_identities = {(item.tool, item.path) for item in snapshots}
    counts = tuple(sorted(Counter(tool for tool, _path in report_identities).items()))
    return JavaReportEvidence(
        counts,
        parsed.findings,
        parsed.tests,
        parsed.coverage,
        debt,
        baseline_present,
    )


@dataclass(frozen=True)
class _ParsedReports:
    findings: tuple[JavaFinding, ...]
    tests: junit.JUnitReport | None
    coverage: tuple[JacocoCoverageFact, ...]


@dataclass(frozen=True)
class JacocoCoverageFact:
    """One real report's explicit aggregate or project coverage label."""

    scope: str
    label: str
    coverage: jacoco.JacocoCoverage


def _parse_reports(
    gradle_root: Path,
    snapshots: tuple[ReportSnapshot, ...],
) -> _ParsedReports:
    findings: list[JavaFinding] = []
    test_reports: list[junit.JUnitReport] = []
    coverage_facts: list[JacocoCoverageFact] = []
    seen: set[tuple[str, str]] = set()
    for snapshot in snapshots:
        identity = snapshot.tool, snapshot.path
        if identity in seen:
            continue
        seen.add(identity)
        report_path = _confined_report_path(gradle_root, snapshot.path)
        coverage = _parse_report(snapshot.tool, report_path, gradle_root, findings, test_reports)
        if coverage is not None:
            coverage_facts.append(
                JacocoCoverageFact(
                    snapshot.coverage_scope,
                    snapshot.coverage_label,
                    coverage,
                )
            )
    ordered = tuple(sorted(findings, key=_finding_sort_key))
    ordered_coverage = tuple(sorted(coverage_facts, key=lambda item: (item.scope, item.label)))
    return _ParsedReports(ordered, _aggregate_tests(test_reports), ordered_coverage)


def _parse_report(
    tool: str,
    report_path: Path,
    gradle_root: Path,
    findings: list[JavaFinding],
    test_reports: list[junit.JUnitReport],
) -> jacoco.JacocoCoverage | None:
    try:
        return _dispatch_report(tool, report_path, gradle_root, findings, test_reports)
    except JavaConfigurationError as exc:
        raise JavaReportEvidenceError(str(exc)) from exc


def _dispatch_report(
    tool: str,
    report_path: Path,
    gradle_root: Path,
    findings: list[JavaFinding],
    test_reports: list[junit.JUnitReport],
) -> jacoco.JacocoCoverage | None:
    if tool in SUPPORTED_STATIC_TOOLS:
        findings.extend(_parse_static_report(tool, report_path, gradle_root))
        return None
    if tool == "test":
        test_reports.append(junit.parse_junit_report(report_path))
        return None
    if tool == "jacoco":
        return jacoco.parse_jacoco_report(report_path)
    raise JavaReportEvidenceError(f"unsupported Java report tool: {tool}")


def _parse_static_report(
    tool: str,
    report_path: Path,
    gradle_root: Path,
) -> tuple[JavaFinding, ...]:
    if tool == "checkstyle":
        return checkstyle.parse_checkstyle_report(
            report_path,
            gradle_root=gradle_root,
        ).findings
    if tool == "pmd":
        return pmd.parse_pmd_report(report_path, gradle_root=gradle_root).findings
    return spotbugs.parse_spotbugs_report(
        report_path,
        gradle_root=gradle_root,
    ).findings


def _confined_report_path(gradle_root: Path, relative_path: str) -> Path:
    canonical_root = gradle_root.resolve(strict=True)
    try:
        path = (canonical_root / relative_path).resolve(strict=True)
    except OSError as exc:
        raise JavaReportEvidenceError("Java report path disappeared before parsing") from exc
    try:
        path.relative_to(canonical_root)
    except ValueError as exc:
        message = "Java report path escapes Gradle root before parsing"
        raise JavaReportEvidenceError(message) from exc
    if not path.is_file():
        raise JavaReportEvidenceError("Java report path is not a file before parsing")
    return path


def _aggregate_tests(reports: list[junit.JUnitReport]) -> junit.JUnitReport | None:
    if not reports:
        return None
    return junit.JUnitReport(
        sum(report.tests for report in reports),
        sum(report.failures for report in reports),
        sum(report.errors for report in reports),
        sum(report.skipped for report in reports),
        tuple(problem for report in reports for problem in report.problems),
    )


def _compare_findings(
    workspace: Path,
    configured_path: str,
    findings: tuple[JavaFinding, ...],
    selected_tools: frozenset[str],
) -> tuple[baseline.FindingDebtReport | None, bool]:
    if not selected_tools:
        return None, False
    baseline_path = _confined_baseline_path(workspace, configured_path)
    if not baseline_path.exists():
        return baseline.FindingDebtReport(len(findings), (), 0, 0), False
    try:
        stored = baseline.read_baseline(baseline_path)
    except (OSError, ValueError) as exc:
        raise JavaReportEvidenceError(f"invalid Java findings baseline: {exc}") from exc
    selected = baseline.JavaFindingsBaseline(
        stored.version,
        stored.provenance,
        tuple(entry for entry in stored.entries if entry.tool in selected_tools),
    )
    return baseline.compare_baseline(selected, findings), True


def _confined_baseline_path(workspace: Path, configured_path: str) -> Path:
    canonical_workspace = workspace.resolve(strict=True)
    candidate = (canonical_workspace / configured_path).resolve(strict=False)
    try:
        candidate.relative_to(canonical_workspace)
    except ValueError as exc:
        raise JavaReportEvidenceError("Java findings baseline escapes workspace") from exc
    return candidate


def _finding_sort_key(finding: JavaFinding) -> tuple[str, int, int]:
    return finding.fingerprint, finding.line or 0, finding.metric or -1


def _finding_payload(finding: JavaFinding) -> dict[str, Any]:
    return {
        "tool": _fact_text(finding.tool),
        "rule": _fact_text(finding.rule),
        "path": _fact_text(finding.path, limit=MAX_ARTIFACT_PATH_TEXT),
        "subject": _fact_text(finding.subject),
        "message": _fact_text(finding.message),
        "severity": _fact_text(finding.severity),
        "line": finding.line,
        "metric": finding.metric,
        "fingerprint": finding.fingerprint,
    }


def _tests_payload(report: junit.JUnitReport) -> dict[str, object]:
    problems = tuple(_problem_payload(problem) for problem in report.problems)
    return {
        "tests": report.tests,
        "failures": report.failures,
        "errors": report.errors,
        "skipped": report.skipped,
        "problems": problems[:MAX_ARTIFACT_PROBLEMS],
        "problems_truncated": len(problems) > MAX_ARTIFACT_PROBLEMS,
    }


def _coverage_payload(fact: JacocoCoverageFact) -> dict[str, str]:
    return {
        "scope": fact.scope,
        "label": fact.label,
        "line_percentage": str(fact.coverage.line.percentage),
        "branch_percentage": str(fact.coverage.branch.percentage),
    }


def _debt_payload(
    report: baseline.FindingDebtReport,
    baseline_present: bool,
) -> dict[str, object]:
    regressions = tuple(asdict(item) for item in report.regressions)
    return {
        "present": baseline_present,
        "passed": report.passed,
        "new_occurrences": report.new_occurrences,
        "metric_regressions": regressions[:MAX_ARTIFACT_FINDINGS],
        "metric_regressions_truncated": len(regressions) > MAX_ARTIFACT_FINDINGS,
        "improved_occurrences": report.improved_occurrences,
        "resolved_occurrences": report.resolved_occurrences,
    }


def _problem_payload(problem: junit.JUnitProblem) -> dict[str, str]:
    return {
        "suite": _fact_text(problem.suite),
        "testcase": _fact_text(problem.testcase),
        "kind": _fact_text(problem.kind),
        "message": _fact_text(problem.message),
        "details": _fact_text(problem.details),
    }


def _fact_text(value: str, *, limit: int = MAX_ARTIFACT_FACT_TEXT) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:limit]
