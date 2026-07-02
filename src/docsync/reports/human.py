"""Human-readable DocSync reports."""

from __future__ import annotations

from docsync.core.models import CheckResult, Finding, LineSpan


def render_check_result(result: CheckResult) -> str:
    """Render a concise human report for a check result."""
    if result.ok:
        return f"DocSync {result.command} passed."
    header = f"DocSync {result.command} found {len(result.findings)} finding(s)."
    lines = [header]
    for finding in result.findings:
        lines.extend(_render_finding(finding))
    return "\n".join(lines)


def _render_finding(finding: Finding) -> list[str]:
    severity = finding.severity.upper()
    rendered = [
        f"{finding.code} {severity} {finding.message}",
    ]
    for location in finding.locations:
        rendered.append(f"  at {_render_span(location)}")
    if finding.related_claims:
        claims = ", ".join(finding.related_claims)
        rendered.append(f"  claims: {claims}")
    if finding.related_evidence:
        evidence = ", ".join(finding.related_evidence)
        rendered.append(f"  evidence: {evidence}")
    return rendered


def _render_span(span: LineSpan) -> str:
    path = span.path.as_posix()
    return f"{path}:L{span.start_line}-L{span.end_line}"
