"""SARIF formatter for DocSync findings."""

from __future__ import annotations

import json
from typing import Any

from docsync.core.models import CheckResult, Finding

SARIF_VERSION = "2.1.0"


def sarif_payload(result: CheckResult) -> dict[str, Any]:
    """Return SARIF payload for DocSync findings."""
    return {
        "version": SARIF_VERSION,
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "DocSync",
                        "informationUri": "https://github.com/douglasmonsky/agent-maintainer",
                        "rules": _rules(result.findings),
                    }
                },
                "results": [_result(finding) for finding in result.findings],
            }
        ],
    }


def write_sarif(result: CheckResult) -> None:
    """Write a SARIF file beside the configured JSON report."""
    path = result.config.report_json.with_suffix(".sarif.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(sarif_payload(result), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


def _rules(findings: tuple[Finding, ...]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    rules: list[dict[str, Any]] = []
    for finding in findings:
        if finding.code in seen:
            continue
        seen.add(finding.code)
        rules.append(
            {
                "id": finding.code,
                "name": finding.code,
                "shortDescription": {"text": finding.code},
            }
        )
    return rules


def _result(finding: Finding) -> dict[str, Any]:
    return {
        "ruleId": finding.code,
        "level": _level(finding.severity),
        "message": {"text": finding.message},
        "locations": [_location(location) for location in finding.locations],
    }


def _location(location: Any) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": location.path.as_posix()},
            "region": {
                "startLine": location.start_line,
                "endLine": location.end_line,
            },
        }
    }


def _level(severity: str) -> str:
    if severity in {"critical", "high", "error"}:
        return "error"
    if severity == "medium":
        return "warning"
    return "note"
