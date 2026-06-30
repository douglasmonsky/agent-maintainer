"""Render advisory mutation sweep reports."""

from __future__ import annotations

import json

from agent_maintainer.runners import mutmut_stats
from agent_maintainer.test_intel.mutation_sweep import (
    MutationSweepCandidate,
    MutationSweepReport,
)
from agent_maintainer.test_intel.mutation_sweep_execution import (
    MutationSweepCandidateResult,
    MutationSweepExecutionReport,
)


def render_text(report: MutationSweepReport) -> str:
    """Return human-readable mutation sweep output."""

    lines = ["Mutation sweep candidates", ""]
    if report.changed_only:
        lines.extend(render_changed_source(report.changed_source))
    lines.extend(render_stop_conditions(report.stop_conditions))
    if not report.candidates:
        lines.extend(("- <none>", "", f"Note: {report.note}"))
        return "\n".join(lines).rstrip()
    for index, candidate in enumerate(report.candidates, start=1):
        lines.extend(render_candidate(index, candidate))
    lines.extend(("Suggested workflow:", f"- {report.note}"))
    return "\n".join(lines).rstrip()


def render_changed_source(changed_source: tuple[str, ...]) -> list[str]:
    """Return changed-source lines."""

    lines = ["Changed source:"]
    if changed_source:
        lines.extend(f"- {path}" for path in changed_source)
    else:
        lines.append("- <none>")
    lines.append("")
    return lines


def render_stop_conditions(stop_conditions: tuple[str, ...]) -> list[str]:
    """Return configured stop lines."""

    lines = ["Stop conditions:"]
    lines.extend(f"- {condition}" for condition in stop_conditions)
    lines.append("")
    return lines


def render_candidate(index: int, candidate: MutationSweepCandidate) -> list[str]:
    """Return text for one mutation sweep candidate."""

    reasons = "; ".join(candidate.reasons)
    tests = ", ".join(candidate.likely_tests) if candidate.likely_tests else "<none>"
    targets = ", ".join(candidate.target_qualnames) if candidate.target_qualnames else "<none>"
    return [
        f"{index}. Sweep candidate: {candidate.path}",
        f"   Score: {candidate.score}",
        f"   Reasons: {reasons}",
        f"   Targets: {targets}",
        f"   Likely tests: {tests}",
        f"   Suggested only_mutate: {candidate.suggested_only_mutate}",
        f"   Verify: {candidate.suggested_command}",
        "",
    ]


def render_json(report: MutationSweepReport) -> str:
    """Return JSON mutation sweep output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)


def render_execution_text(report: MutationSweepExecutionReport) -> str:
    """Return compact execution output."""

    status = "failed" if report.has_failures else "passed"
    lines = [
        "Mutation sweep execution",
        label_line("Run id", report.run_id),
        label_line("Artifacts", report.artifact_dir),
        "",
    ]
    if not report.results:
        lines.append("- <no candidates executed>")
    for result in report.results:
        lines.extend(render_execution_result(result))
    if report.stopped_reason:
        lines.append(label_line("Stopped", report.stopped_reason))
    lines.append(label_line("Status", status))
    return "\n".join(lines).rstrip()


def render_execution_result(result: MutationSweepCandidateResult) -> list[str]:
    """Return compact text for one executed candidate."""

    stats = execution_stats_summary(result.stats)
    readiness = "promotion-ready" if result.promotion_ready else "not promotion-ready"
    candidate_path = result.candidate.path
    candidate_score = result.candidate.score
    lines = [
        f"- {candidate_path}",
        label_line("  score", candidate_score),
        label_line("  result", result.status),
        label_line("  mutmut", stats),
        label_line("  promotion", readiness),
        label_line("  artifacts", result.run_log.parent),
    ]
    if result.error:
        lines.append(label_line("  error", result.error))
    return lines


def render_execution_json(report: MutationSweepExecutionReport) -> str:
    """Return JSON execution output."""

    return json.dumps(report.to_json(), indent=2, sort_keys=True)


def execution_stats_summary(stats: mutmut_stats.MutmutStats | None) -> str:
    """Return compact Mutmut stats for execution output."""

    if stats is None:
        return "no stats"
    return mutmut_stats.render_summary(stats)


def label_line(label: str, value: object) -> str:
    """Return simple label line."""

    return f"{label}: {value}"
