"""Bounded SpotBugs reports and deterministic native baselines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.java import JavaReportExpectation
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.java.findings import JavaFinding
from agent_maintainer.ecosystems.java.observations import (
    GradleObservation,
    GradleTaskState,
    ReportSnapshot,
    snapshot_reports,
)
from agent_maintainer.ecosystems.java.reports import xml as java_xml
from agent_maintainer.ecosystems.java.reports.xml import (
    JavaXmlError,
    XmlElement,
    XmlLimits,
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

    findings: tuple[JavaFinding, ...]
    native_findings: tuple[SpotBugsFinding, ...]


def parse_spotbugs_report(
    path: Path,
    *,
    gradle_root: Path,
    limits: XmlLimits | None = None,
) -> SpotBugsReport:
    """Parse canonical and native-filter findings from bounded XML."""
    selected_limits = limits or XmlLimits()
    root = java_xml.parse_bounded_xml(path, limits=selected_limits)
    if java_xml.local_name(root.tag) != "BugCollection":
        raise JavaXmlError("unsupported SpotBugs report root")
    _validate_analysis_errors(root)
    bug_instances = tuple(
        element for element in root.iter() if java_xml.local_name(element.tag) == "BugInstance"
    )
    if len(bug_instances) > selected_limits.max_findings:
        raise JavaXmlError("SpotBugs report exceeds finding limit")
    parsed = tuple(_parse_finding(element, gradle_root=gradle_root) for element in bug_instances)
    return SpotBugsReport(
        tuple(item[0] for item in parsed),
        tuple(item[1] for item in parsed),
    )


def create_spotbugs_baseline(
    gradle_root: Path,
    expectation: JavaReportExpectation,
    observation: GradleObservation,
) -> str:
    """Create native filter XML from complete successful task-scoped evidence."""
    current = _validated_current_reports(gradle_root, expectation, observation)
    findings: set[SpotBugsFinding] = set()
    for snapshot in current:
        report = parse_spotbugs_report(
            gradle_root / snapshot.path,
            gradle_root=gradle_root,
        )
        findings.update(report.native_findings)
    return _render_native_filter(tuple(sorted(findings)))


def validate_spotbugs_evidence(
    gradle_root: Path,
    expectation: JavaReportExpectation,
    observation: GradleObservation,
) -> tuple[SpotBugsReport, ...]:
    """Validate current SpotBugs XML without creating or changing a baseline."""
    current = _validated_current_reports(gradle_root, expectation, observation)
    return tuple(
        parse_spotbugs_report(
            gradle_root / snapshot.path,
            gradle_root=gradle_root,
        )
        for snapshot in current
    )


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
    expected = {task.removeprefix(":") for task in expectation.tasks}
    states = {
        outcome.state
        for outcome in observation.task_outcomes
        if outcome.task.removeprefix(":") in expected
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


def _parse_finding(
    element: XmlElement,
    *,
    gradle_root: Path,
) -> tuple[JavaFinding, SpotBugsFinding]:
    bug_type = element.attrib.get("type", "").strip()
    if not bug_type:
        raise JavaXmlError("SpotBugs BugInstance is missing type")
    class_element = _first_child(element, "Class")
    class_name = "" if class_element is None else class_element.attrib.get("classname", "").strip()
    if not class_name:
        raise JavaXmlError("SpotBugs BugInstance is missing class identity")
    method = _first_child(element, "Method")
    native = SpotBugsFinding(
        bug_type,
        class_name,
        "" if method is None else method.attrib.get("name", "").strip(),
        "" if method is None else method.attrib.get("signature", "").strip(),
    )
    try:
        finding = JavaFinding(
            tool="spotbugs",
            rule=bug_type,
            path=_source_path(element, class_name, gradle_root=gradle_root),
            subject=_subject(native),
            message=_message(element, bug_type),
            severity=_severity(element.attrib.get("priority")),
            line=_source_line(element),
        )
    except ValueError as exc:
        raise JavaXmlError("malformed SpotBugs finding") from exc
    return finding, native


def _source_path(element: XmlElement, class_name: str, *, gradle_root: Path) -> str:
    source_line = _first_child(element, "SourceLine")
    reported = "" if source_line is None else source_line.attrib.get("sourcepath", "")
    class_path = class_name.split("$", maxsplit=1)[0].replace(".", "/")
    fallback = f"{class_path}.java"
    return java_xml.normalized_report_path(reported or fallback, gradle_root=gradle_root)


def _source_line(element: XmlElement) -> int | None:
    source_line = _first_child(element, "SourceLine")
    value = None if source_line is None else source_line.attrib.get("start")
    if value is None or not value.strip():
        return None
    try:
        line = int(value)
    except ValueError as exc:
        raise JavaXmlError("malformed SpotBugs source line") from exc
    if line < 1:
        raise JavaXmlError("malformed SpotBugs source line")
    return line


def _subject(finding: SpotBugsFinding) -> str:
    if not finding.method_name:
        return finding.class_name
    return f"{finding.class_name}#{finding.method_name}{finding.method_signature}"


def _message(element: XmlElement, fallback: str) -> str:
    for child_name in ("ShortMessage", "LongMessage"):
        child = _first_child(element, child_name)
        if child is not None and (child.text or "").strip():
            return java_xml.bounded_report_text(child.text or "", fallback=fallback)
    return fallback


def _severity(value: str | None) -> str:
    if value is None or not value.strip():
        return "warning"
    try:
        priority = int(value)
    except ValueError as exc:
        raise JavaXmlError("malformed SpotBugs priority") from exc
    severities = {1: "error", 2: "warning", 3: "info"}
    if priority not in severities:
        raise JavaXmlError("malformed SpotBugs priority")
    return severities[priority]


def _first_child(element: XmlElement, name: str) -> XmlElement | None:
    return next(
        (child for child in element if java_xml.local_name(child.tag) == name),
        None,
    )


def _validate_analysis_errors(root: XmlElement) -> None:
    errors = next(
        (item for item in root.iter() if java_xml.local_name(item.tag) == "Errors"),
        None,
    )
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
    root = java_xml.new_xml_element("FindBugsFilter")
    for finding in findings:
        match = java_xml.append_xml_element(root, "Match", {})
        java_xml.append_xml_element(match, "Bug", {"pattern": finding.bug_type})
        java_xml.append_xml_element(match, "Class", {"name": finding.class_name})
        if finding.method_name:
            attributes = {"name": finding.method_name}
            if finding.method_signature:
                attributes["signature"] = finding.method_signature
            java_xml.append_xml_element(match, "Method", attributes)
    body = java_xml.serialize_xml(root)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'
