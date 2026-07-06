"""Render local agent efficacy reports."""

from __future__ import annotations

from agent_maintainer.assess.efficacy_models import EfficacyMetric, EfficacyReport


def render_text(report: EfficacyReport) -> str:
    """Render compact efficacy report text."""

    lines = [
        "Agent Efficacy Metrics",
        f"Events: {report.total_events} from {report.files_read} files",
        f"Malformed lines: {report.malformed_lines}",
        "",
        "Metrics",
    ]
    lines.extend(_metric_line(metric) for metric in report.metrics)
    lines.append("")
    lines.append("Sources")
    lines.extend(f"- {source}" for source in report.sources)
    lines.append("")
    lines.append("Limitations")
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    return "\n".join(lines)


def _metric_line(metric: EfficacyMetric) -> str:
    ratio = ""
    if metric.numerator is not None and metric.denominator is not None:
        ratio = f" ({metric.numerator}/{metric.denominator})"
    return f"- {metric.name}: {metric.value} {metric.unit} [{metric.kind}]{ratio} - {metric.detail}"
