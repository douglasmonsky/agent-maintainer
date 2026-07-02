"""JSON report writer for DocSync."""

from __future__ import annotations

import json

from docsync.core.models import CheckResult


def write_report_json(result: CheckResult) -> None:
    """Write configured JSON report for a check result."""
    result.config.report_json.parent.mkdir(parents=True, exist_ok=True)
    result.config.report_json.write_text(
        f"{json.dumps(result.to_json(), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
