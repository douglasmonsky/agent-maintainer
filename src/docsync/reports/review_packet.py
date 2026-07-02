"""Agent-oriented DocSync review packets."""

from __future__ import annotations

from typing import Any

from docsync.core.models import CheckResult


def review_packet_for_result(result: CheckResult) -> dict[str, Any]:
    """Return a compact JSON-ready review packet."""
    return {
        "version": 1,
        "command": result.command,
        "base_ref": result.base_ref,
        "ok": result.ok,
        "findings": [finding.to_json() for finding in result.findings],
    }


def review_prompt_for_result(result: CheckResult) -> str:
    """Return Markdown prompt for agent review."""
    base_ref = result.base_ref or "n/a"
    lines = [
        "# DocSync Review Packet",
        "",
        f"Command: `{result.command}`",
        f"Base ref: `{base_ref}`",
        "",
    ]
    if result.ok:
        lines.append("No DocSync findings require review.")
        return _lines_text(lines)
    for finding in result.findings:
        lines.extend([f"## {finding.code}", "", finding.message, ""])
        for location in finding.locations:
            path = location.path.as_posix()
            lines.append(f"- `{path}:L{location.start_line}-L{location.end_line}`")
        if finding.related_claims:
            claims = ", ".join(finding.related_claims)
            lines.append(f"- Claims: `{claims}`")
        if finding.related_evidence:
            evidence = ", ".join(finding.related_evidence)
            lines.append(f"- Evidence: `{evidence}`")
        lines.append("")
    return "\n".join(lines)


def _lines_text(lines: list[str]) -> str:
    text = "\n".join(lines)
    return f"{text}\n"
