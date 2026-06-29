"""Render named sections in the static verification report."""

from __future__ import annotations

from html import escape
from typing import Any

from agent_maintainer.report.markdown import summary_markdown_section
from agent_maintainer.report.tables import check_table, list_items, local_href, text
from agent_maintainer.report.types import NamedCheckSection, ReportPaths

SUCCESS_STATUS = "passed"
WARNING_STATUS = "warning"
SKIPPED_STATUS = "skipped"
FAILED_STATUS = "failed"
ARCHITECTURE_CHECKS = frozenset(
    (
        "architecture-decision",
        "import-linter",
        "tach",
        "tach-config",
    ),
)
COVERAGE_CHECKS = frozenset(
    (
        "diff-cover",
        "pytest-coverage",
    ),
)
COVERAGE_SECTION = NamedCheckSection("coverage", "Coverage", COVERAGE_CHECKS)
ARCHITECTURE_SECTION = NamedCheckSection(
    "architecture",
    "Architecture",
    ARCHITECTURE_CHECKS,
)
RELEASE_CHECK_PREFIXES = (
    "actionlint",
    "pip-audit",
    "sbom",
    "secret-scan",
    "twine",
    "zizmor",
)


def render_sections(
    payload: dict[str, Any],
    *,
    checks: list[dict[str, Any]],
    paths: ReportPaths,
    pr_summary: str,
    last_failure: str,
) -> tuple[str, ...]:
    """Render all static report sections in display order."""
    leading_sections = [
        _summary_section(payload, checks, paths),
        _failed_checks_section(checks, paths),
        _markdown_section("test-intelligence", "Test Intelligence", pr_summary),
        _markdown_section("ratchet-status", "Ratchet Status", pr_summary),
        _markdown_section("change-plan-status", "Change Plan Status", pr_summary),
        _context_section(paths, pr_summary),
    ]
    focused_sections = [
        _named_checks_section(COVERAGE_SECTION, checks, paths, payload),
        _named_checks_section(ARCHITECTURE_SECTION, checks, paths),
        _release_section(checks, paths, last_failure),
    ]
    return tuple(leading_sections + focused_sections)


def header_html(payload: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    """Render static report header."""
    result = "FAIL" if _failed_checks(checks) else "PASS"
    generated_at = text(payload.get("generated_at"), "unknown")
    return (
        '<header class="hero">'
        "<h1>Agent Maintainer Verification Report</h1>"
        f"<p>Result: <strong>{escape(result)}</strong> · Generated: "
        f"<time>{escape(generated_at)}</time></p>"
        "</header>"
    )


def _summary_section(
    payload: dict[str, Any],
    checks: list[dict[str, Any]],
    paths: ReportPaths,
) -> str:
    rows = {
        "Profile": text(payload.get("profile"), "unknown"),
        "Base ref": text(payload.get("base_ref"), "unknown"),
        "Compare branch": text(payload.get("compare_branch"), "unknown"),
        "Checks": str(len(checks)),
    }
    metrics = "".join(
        _metric_html(label, str(_status_count(checks, status)))
        for status, label in (
            (FAILED_STATUS, "Failed"),
            (WARNING_STATUS, "Warnings"),
            (SKIPPED_STATUS, "Skipped"),
            (SUCCESS_STATUS, "Passed"),
        )
    )
    details = "".join(_metric_html(label, value) for label, value in rows.items())
    body = (
        f'<div class="grid">{details}{metrics}</div>'
        f"{check_table(checks, paths.log_dir, paths.output_dir, include_expansion=False)}"
    )
    return _panel("verification-summary", "Verification Summary", body)


def _failed_checks_section(checks: list[dict[str, Any]], paths: ReportPaths) -> str:
    failures = _failed_checks(checks)
    if not failures:
        return _panel("failed-checks", "Failed Checks", "<p>No failed checks.</p>")
    table = check_table(failures, paths.log_dir, paths.output_dir, include_expansion=True)
    return _panel("failed-checks", "Failed Checks", table)


def _markdown_section(section_id: str, title: str, pr_summary: str) -> str:
    body = summary_markdown_section(pr_summary, title)
    if not body:
        body = "No data in latest PR summary artifact."
    return _panel(section_id, title, f"<pre>{escape(body)}</pre>")


def _context_section(paths: ReportPaths, pr_summary: str) -> str:
    section = summary_markdown_section(pr_summary, "Context Pack Path")
    pack_path = paths.log_dir / "context" / "PACK.md"
    link = ""
    if pack_path.exists():
        href = local_href(pack_path, paths.output_dir)
        link = f'<p><a href="{href}">Open context pack</a></p>'
    body = f"{link}<pre>{escape(section or 'Context pack not generated.')}</pre>"
    return _panel("context-pack-links", "Context Pack Links", body)


def _named_checks_section(
    section: NamedCheckSection,
    checks: list[dict[str, Any]],
    paths: ReportPaths,
    payload: dict[str, Any] | None = None,
) -> str:
    selected = [check for check in checks if text(check.get("name"), "") in section.names]
    threshold_html = ""
    if isinstance(payload, dict):
        threshold_html = _threshold_html(payload)
    if not selected:
        body = f"{threshold_html}<p>No matching checks.</p>"
        return _panel(section.section_id, section.title, body)
    table = check_table(selected, paths.log_dir, paths.output_dir, include_expansion=False)
    return _panel(section.section_id, section.title, f"{threshold_html}{table}")


def _release_section(
    checks: list[dict[str, Any]],
    paths: ReportPaths,
    last_failure: str,
) -> str:
    selected = [
        check for check in checks if text(check.get("name"), "").startswith(RELEASE_CHECK_PREFIXES)
    ]
    table = "<p>No release-readiness checks in manifest.</p>"
    if selected:
        table = check_table(selected, paths.log_dir, paths.output_dir, include_expansion=False)
    failure_note = ""
    if last_failure:
        failure_note = f"<h3>Latest Failure Note</h3><pre>{escape(last_failure)}</pre>"
    return _panel("release-readiness", "Release Readiness", f"{table}{failure_note}")


def _panel(section_id: str, title: str, body: str) -> str:
    return f'<section id="{section_id}" class="panel"><h2>{escape(title)}</h2>{body}</section>'


def _metric_html(label: str, value: str) -> str:
    return f'<div class="metric"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def _threshold_html(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        return ""
    items = [f"{key}: {value}" for key, value in sorted(thresholds.items())]
    return f"<p><strong>Thresholds:</strong></p>{list_items(items)}"


def _failed_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [check for check in checks if text(check.get("status"), "") == FAILED_STATUS]


def _status_count(checks: list[dict[str, Any]], status: str) -> int:
    return sum(1 for check in checks if text(check.get("status"), "") == status)
