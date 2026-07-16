"""Bounded SpotBugs reports and deterministic native baselines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.java import JavaReportExpectation
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.java.observations import (
    GradleObservation,
    GradleTaskState,
    ReportSnapshot,
    snapshot_reports,
)
from agent_maintainer.ecosystems.java.reports.xml import (
    JavaXmlError,
    XmlElement,
    XmlLimits,
    append_xml_element,
    local_name,
    new_xml_element,
    parse_bounded_xml,
    serialize_xml,
)


class SpotBugsEvidenceError(JavaConfigurationError):
    """Raised when task-scoped evidence cannot authorize a native baseline."""


@dataclass(frozen=True, order=True)
class SpotBugsFinding:
    """Identity fields accepted by a SpotBugs native filter."""

    bug_type: str
    class_name: str
    method_name: str = ""
    method_signature: str = ""


@dataclass(frozen=True)
class SpotBugsReport:
    """One validated SpotBugs report."""

    findings: tuple[SpotBugsFinding, ...]


def parse_spotbugs_report(
    path: Path,
    *,
    limits: XmlLimits | None = None,
) -> SpotBugsReport:
    """Parse the native-filter identity subset from a bounded SpotBugs report."""
    selected_limits = limits or XmlLimits()
    root = parse_bounded_xml(path, limits=selected_limits)
    if local_name(root.tag) != "BugCollection":
        raise JavaXmlError("unsupported SpotBugs report root")
    _validate_analysis_errors(root)
    bug_instances = tuple(
        element for element in root.iter() if local_name(element.tag) == "BugInstance"
    )
    if len(bug_instances) > selected_limits.max_findings:
        raise JavaXmlError("SpotBugs report exceeds finding limit")
    return SpotBugsReport(tuple(_parse_finding(element) for element in bug_instances))


def create_spotbugs_baseline(
    gradle_root: Path,
    expectation: JavaReportExpectation,
    observation: GradleObservation,
) -> str:
    """Create native filter XML from complete successful task-scoped evidence."""
    current = _validated_current_reports(gradle_root, expectation, observation)
    findings: set[SpotBugsFinding] = set()
    for snapshot in current:
        report = parse_spotbugs_report(gradle_root / snapshot.path)
        findings.update(report.findings)
    return _render_native_filter(tuple(sorted(findings)))


def validate_spotbugs_evidence(
    gradle_root: Path,
    expectation: JavaReportExpectation,
    observation: GradleObservation,
) -> tuple[SpotBugsReport, ...]:
    """Validate current SpotBugs XML without creating or changing a baseline."""
    current = _validated_current_reports(gradle_root, expectation, observation)
    return tuple(parse_spotbugs_report(gradle_root / snapshot.path) for snapshot in current)


def verification_payload(
    gradle_root: Path,
    baseline_path: str,
    expectations: tuple[JavaReportExpectation, ...],
    observation: GradleObservation,
) -> dict[str, int] | None:
    """Return read-only native-ratchet evidence for runner artifacts."""
    if not baseline_path or observation.exit_code != 0:
        return None
    reports: list[SpotBugsReport] = []
    for expectation in expectations:
        if expectation.tool == "spotbugs":
            reports.extend(validate_spotbugs_evidence(gradle_root, expectation, observation))
    if not reports:
        raise SpotBugsEvidenceError("required SpotBugs report expectation is missing")
    return {
        "reports": len(reports),
        "findings": sum(len(report.findings) for report in reports),
    }


def _validated_current_reports(
    gradle_root: Path,
    expectation: JavaReportExpectation,
    observation: GradleObservation,
) -> tuple[ReportSnapshot, ...]:
    if observation.exit_code != 0:
        raise SpotBugsEvidenceError("Gradle run failed; refusing SpotBugs baseline evidence")
    states = _expectation_states(expectation, observation)
    invalid_states = states - {
        GradleTaskState.SUCCESS,
        GradleTaskState.FROM_CACHE,
        GradleTaskState.UP_TO_DATE,
    }
    if invalid_states:
        raise SpotBugsEvidenceError("SpotBugs task did not produce successful report evidence")
    current = snapshot_reports(gradle_root, (expectation,), observation.requested_tasks)
    if expectation.required:
        observed_globs = {snapshot.glob for snapshot in current}
        if any(pattern not in observed_globs for pattern in expectation.globs):
            raise SpotBugsEvidenceError("required SpotBugs report evidence is missing")
    _reject_stale_success(current, observation.pre_run_reports, states)
    return current


def _expectation_states(
    expectation: JavaReportExpectation,
    observation: GradleObservation,
) -> set[GradleTaskState]:
    expected = {_normalized_task(task) for task in expectation.tasks}
    states = {
        outcome.state
        for outcome in observation.task_outcomes
        if _normalized_task(outcome.task) in expected
    }
    if len(states) == 0:
        raise SpotBugsEvidenceError("SpotBugs task outcome evidence is incomplete")
    return states


def _reject_stale_success(
    current: tuple[ReportSnapshot, ...],
    pre_run: tuple[ReportSnapshot, ...],
    states: set[GradleTaskState],
) -> None:
    if GradleTaskState.SUCCESS not in states:
        return
    previous = {(snapshot.tool, snapshot.path): snapshot.sha256 for snapshot in pre_run}
    if any(previous.get((snapshot.tool, snapshot.path)) == snapshot.sha256 for snapshot in current):
        raise SpotBugsEvidenceError("SpotBugs report evidence is stale after executed task success")


def _parse_finding(element: XmlElement) -> SpotBugsFinding:
    bug_type = element.attrib.get("type", "").strip()
    if not bug_type:
        raise JavaXmlError("SpotBugs BugInstance is missing type")
    class_element = _first_child(element, "Class")
    class_name = "" if class_element is None else class_element.attrib.get("classname", "").strip()
    if not class_name:
        raise JavaXmlError("SpotBugs BugInstance is missing class identity")
    method = _first_child(element, "Method")
    return SpotBugsFinding(
        bug_type,
        class_name,
        "" if method is None else method.attrib.get("name", "").strip(),
        "" if method is None else method.attrib.get("signature", "").strip(),
    )


def _first_child(element: XmlElement, name: str) -> XmlElement | None:
    return next((child for child in element if local_name(child.tag) == name), None)


def _validate_analysis_errors(root: XmlElement) -> None:
    errors = next((item for item in root.iter() if local_name(item.tag) == "Errors"), None)
    if errors is None:
        return
    error_count, missing_classes = _analysis_error_counts(errors)
    if error_count > 0 or missing_classes > 0:
        raise JavaXmlError("incomplete SpotBugs analysis report")


def _analysis_error_counts(errors: XmlElement) -> tuple[int, int]:
    try:
        return int(errors.attrib.get("errors", "0")), int(errors.attrib.get("missingClasses", "0"))
    except ValueError as exc:
        raise JavaXmlError("malformed SpotBugs analysis error counts") from exc


def _render_native_filter(findings: tuple[SpotBugsFinding, ...]) -> str:
    root = new_xml_element("FindBugsFilter")
    for finding in findings:
        match = append_xml_element(root, "Match", {})
        append_xml_element(match, "Bug", {"pattern": finding.bug_type})
        append_xml_element(match, "Class", {"name": finding.class_name})
        if finding.method_name:
            attributes = {"name": finding.method_name}
            if finding.method_signature:
                attributes["signature"] = finding.method_signature
            append_xml_element(match, "Method", attributes)
    body = serialize_xml(root)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'


def _normalized_task(task: str) -> str:
    return task if task.startswith(":") else f":{task}"
