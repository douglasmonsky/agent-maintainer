"""Render static HTML reports from verifier diagnostic artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_maintainer.report.sections import header_html, render_sections
from agent_maintainer.report.styles import head_html
from agent_maintainer.report.types import ReportPaths
from agent_maintainer.verify.artifacts import LAST_FAILURE_NAME, MANIFEST_NAME
from agent_maintainer.verify.pr_summary import PR_SUMMARY_NAME

REPORT_DIR = "report"
REPORT_NAME = "index.html"


def generate_html_report(log_dir: Path, output_path: Path | None = None) -> Path:
    """Generate a static HTML report and return its output path."""
    manifest_path = log_dir / MANIFEST_NAME
    payload = _read_manifest(manifest_path)
    target = output_path or log_dir / REPORT_DIR / REPORT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    report_html = render_html_report(
        payload,
        log_dir=log_dir,
        output_path=target,
        pr_summary=_read_optional_text(log_dir / PR_SUMMARY_NAME),
        last_failure=_read_optional_text(log_dir / LAST_FAILURE_NAME),
    )
    target.write_text(report_html, encoding="utf-8")
    return target


def render_html_report(
    payload: dict[str, Any],
    *,
    log_dir: Path,
    output_path: Path,
    pr_summary: str = "",
    last_failure: str = "",
) -> str:
    """Render full static report HTML."""
    checks = _checks(payload)
    paths = ReportPaths(log_dir=log_dir, output_dir=output_path.parent)
    sections = render_sections(
        payload,
        checks=checks,
        paths=paths,
        pr_summary=pr_summary,
        last_failure=last_failure,
    )
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            head_html(),
            "<body>",
            header_html(payload, checks),
            '<main class="report">',
            *sections,
            "</main>",
            "</body>",
            "</html>",
        ),
    )


def _read_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        msg = f"{manifest_path} does not exist; run verification first."
        raise FileNotFoundError(msg)
    with manifest_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        msg = f"{manifest_path} is not a JSON object."
        raise ValueError(msg)
    return payload


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks = payload.get("checks", [])
    if not isinstance(checks, list):
        return []
    return [check for check in checks if isinstance(check, dict)]
