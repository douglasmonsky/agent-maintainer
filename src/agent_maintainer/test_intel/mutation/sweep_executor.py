"""Orchestrate advisory mutation sweep execution."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

from agent_maintainer.runners import mutmut_stats
from agent_maintainer.test_intel.mutation.sweep import MutationSweepReport
from agent_maintainer.test_intel.mutation.sweep_execution import (
    MutationSweepCandidateResult,
    MutationSweepExecutionReport,
    MutationSweepExecutionRequest,
)
from agent_maintainer.test_intel.mutation.sweep_runner import execute_candidate


def execute_mutation_sweep(
    report: MutationSweepReport,
    request: MutationSweepExecutionRequest,
) -> MutationSweepExecutionReport:
    """Run selected mutation sweep candidates in isolated worktrees."""

    started_at = time.monotonic()
    run_id = new_run_id()
    artifact_dir = request.output_dir / run_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    results: list[MutationSweepCandidateResult] = []
    stopped_reason: str | None = None
    candidates = report.candidates[: max(request.candidate_limit, 0)]
    for index, candidate in enumerate(candidates, start=1):
        if time_budget_exhausted(started_at, request.time_budget_minutes):
            stopped_reason = "time budget exhausted"
            break
        result = execute_candidate(candidate, index, artifact_dir, request)
        results.append(result)
        if request.fail_fast and result.failed:
            stopped_reason = f"fail-fast after {candidate.path}"
            break
    execution_report = MutationSweepExecutionReport(
        run_id=run_id,
        artifact_dir=artifact_dir,
        results=tuple(results),
        stopped_reason=stopped_reason,
    )
    write_execution_artifacts(execution_report)
    return execution_report


def write_execution_artifacts(report: MutationSweepExecutionReport) -> None:
    """Write manifest and summary artifacts for an execution run."""

    manifest_path = report.artifact_dir / "manifest.json"
    summary_path = report.artifact_dir / "summary.md"
    manifest_payload = json.dumps(report.to_json(), indent=2, sort_keys=True)
    manifest_path.write_text(
        f"{manifest_payload}\n",
        encoding="utf-8",
    )
    summary_path.write_text(render_summary_markdown(report), encoding="utf-8")


def render_summary_markdown(report: MutationSweepExecutionReport) -> str:
    """Return concise Markdown summary artifact."""

    lines = [
        f"# Mutation Sweep {report.run_id}",
        "",
        f"- Artifacts: `{report.artifact_dir}`",
        f"- Failed runner/config steps: `{report.has_failures}`",
    ]
    if report.stopped_reason:
        lines.append(f"- Stopped: {report.stopped_reason}")
    lines.extend(("", "| Candidate | Result | Mutmut | Promotion |", "| --- | --- | --- | --- |"))
    for result in report.results:
        lines.append(summary_row(result))
    lines.append("")
    return "\n".join(lines)


def summary_row(result: MutationSweepCandidateResult) -> str:
    """Return one Markdown table row."""

    candidate = result.candidate
    promotion_status = "ready" if result.promotion_ready else "not ready"
    return " | ".join(
        (
            "",
            f"`{candidate.path}`",
            result.status,
            stats_summary(result.stats),
            promotion_status,
            "",
        ),
    )


def stats_summary(stats: mutmut_stats.MutmutStats | None) -> str:
    """Return compact stats summary."""

    if stats is None:
        return "no stats"
    return mutmut_stats.render_summary(stats)


def time_budget_exhausted(started_at: float, minutes: int) -> bool:
    """Return whether no more candidates should start."""

    return minutes >= 0 and time.monotonic() - started_at >= minutes * 60


def new_run_id() -> str:
    """Return filesystem-safe mutation sweep run id."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return "-".join((timestamp, suffix))
