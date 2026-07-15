"""Compose changed-source test-intelligence reports."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel.changed import changed_source_paths
from agent_maintainer.test_intel.coverage import coverage_for_changed_sources
from agent_maintainer.test_intel.mapping import likely_tests_for_changes
from agent_maintainer.test_intel.models import TestIntelReport
from agent_maintainer.test_intel.reporting import render_json, render_text, suggested_actions

FORMAT_JSON = "json"


def build(*, base_ref: str, staged: bool, repo_root: Path) -> TestIntelReport:
    """Build changed-source test-intelligence report."""

    config = loader.load_config()
    changed_source = changed_source_paths(config, base_ref=base_ref, staged=staged)
    matches = likely_tests_for_changes(changed_source, config, repo_root)
    coverage = coverage_for_changed_sources(
        repo_root,
        changed_source,
        base_ref=base_ref,
        staged=staged,
    )
    return TestIntelReport(
        changed_source=changed_source,
        likely_tests=matches,
        coverage=coverage,
        suggested_actions=suggested_actions(matches),
    )


def render(report: TestIntelReport, output_format: str) -> str:
    """Render report in the requested output format."""

    if output_format == FORMAT_JSON:
        return render_json(report)
    return render_text(report)
