"""Write diagnostic artifacts for maintainer verifier runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.context import models as context_models
from agent_maintainer.context.budget import bound_text
from agent_maintainer.models import CheckResult
from agent_maintainer.verify import artifact_manifest, pr_summary
from agent_maintainer.verify import history as verify_history
from agent_maintainer.verify import timing as verify_timing
from agent_maintainer.verify.git_state import git_state

MANIFEST_NAME = "manifest.json"
LAST_FAILURE_NAME = "LAST_FAILURE.md"
PR_SUMMARY_NAME = pr_summary.PR_SUMMARY_NAME
TRUNCATION_NOTE_ALLOWANCE = 320


@dataclass(frozen=True)
class RunContext:
    """Context shared by all checks in one verifier run."""

    repo_root: Path
    profile: str
    base_ref: str
    compare_branch: str
    staged: bool
    config: MaintainerConfig
    run_id: str


def write_run_artifacts(
    log_dir: Path,
    context: RunContext,
    results: list[CheckResult],
) -> None:
    """Write latest and run-scoped artifacts for one verifier run."""

    log_dir.mkdir(parents=True, exist_ok=True)
    failures = [result for result in results if not result.passed]
    snapshot_dir = verify_history.run_snapshot_dir(log_dir, context.run_id)
    snapshot_artifacts = verify_history.SnapshotArtifacts(
        failure_snapshot=snapshot_dir / LAST_FAILURE_NAME if failures else None,
        log_path_overrides=verify_history.copy_run_logs(
            snapshot_dir,
            context.repo_root,
            results,
        ),
        context_log_dir=verify_history.path_text(snapshot_dir, context.repo_root),
    )
    write_manifest(
        log_dir,
        context,
        results,
        failure_snapshot=snapshot_artifacts.failure_snapshot,
    )
    write_history_manifest(
        snapshot_dir,
        context,
        results,
        snapshot_artifacts=snapshot_artifacts,
    )
    write_last_failure(
        log_dir,
        context,
        failures,
        failure_snapshot=snapshot_artifacts.failure_snapshot,
        context_log_dir=snapshot_artifacts.context_log_dir,
    )
    verify_history.prune_run_history(log_dir, context.config.diagnostic_run_history_limit)
    verify_history.atomic_write_text(
        log_dir / pr_summary.PR_SUMMARY_NAME,
        pr_summary.render_pr_summary(log_dir=log_dir, context=context, results=results),
    )


def write_manifest(
    log_dir: Path,
    context: RunContext,
    results: list[CheckResult],
    *,
    failure_snapshot: Path | None = None,
) -> None:
    """Write machine-readable metadata for one verifier run."""

    payload = manifest_payload(context, results, failure_snapshot=failure_snapshot)
    verify_history.atomic_write_text(log_dir / MANIFEST_NAME, json_text(payload))


def write_history_manifest(
    snapshot_dir: Path,
    context: RunContext,
    results: list[CheckResult],
    *,
    snapshot_artifacts: verify_history.SnapshotArtifacts,
) -> None:
    """Write run-scoped manifest snapshot for stable agent references."""

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    payload = manifest_payload(
        context,
        results,
        failure_snapshot=snapshot_artifacts.failure_snapshot,
        log_path_overrides=snapshot_artifacts.log_path_overrides,
        context_log_dir=snapshot_artifacts.context_log_dir,
    )
    verify_history.atomic_write_text(snapshot_dir / MANIFEST_NAME, json_text(payload))


def manifest_payload(
    context: RunContext,
    results: list[CheckResult],
    *,
    failure_snapshot: Path | None = None,
    log_path_overrides: dict[str, str] | None = None,
    context_log_dir: str | None = None,
) -> dict[str, object]:
    """Return machine-readable metadata for one verifier run."""

    return {
        "version": 1,
        "run_id": context.run_id,
        "generated_at": verify_timing.utc_timestamp(),
        "profile": context.profile,
        "base_ref": context.base_ref,
        "compare_branch": context.compare_branch,
        "staged": context.staged,
        "failure_snapshot": verify_history.path_text(failure_snapshot, context.repo_root),
        "git": git_state(context.repo_root),
        "timing": verify_timing.run_timing(results),
        "expected_duration_hint": verify_timing.profile_duration_hint(context.profile),
        "thresholds": artifact_manifest.threshold_snapshot(context.config),
        "checks": [
            artifact_manifest.check_payload(
                result,
                context.repo_root,
                context.config,
                log_path_override=(log_path_overrides or {}).get(result.name),
                context_log_dir=context_log_dir,
            )
            for result in results
        ],
    }


def write_last_failure(
    log_dir: Path,
    context: RunContext,
    failures: list[CheckResult],
    *,
    failure_snapshot: Path | None = None,
    context_log_dir: str | None = None,
) -> None:
    """Write or clear the concise last-failure note."""

    path = log_dir / LAST_FAILURE_NAME
    if not failures:
        path.unlink(missing_ok=True)
        return
    snapshot_path = (
        failure_snapshot
        or verify_history.run_snapshot_dir(log_dir, context.run_id) / LAST_FAILURE_NAME
    )
    lines = [
        "# Last Maintainer Failure",
        "",
        f"Run ID: `{context.run_id}`",
        f"Profile: `{context.profile}`",
        f"Rerun: `{rerun_command(context)}`",
        f"Stable snapshot: `{verify_history.path_text(snapshot_path, context.repo_root)}`",
        "",
        "`LAST_FAILURE.md` is the latest pointer and can change after later runs.",
        "",
        "## Failed Checks",
        "",
    ]
    for failure in failures:
        lines.extend(failure_section(failure, context_log_dir=context_log_dir))
    text = bounded_last_failure_text("\n".join(lines).rstrip(), context.config)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    verify_history.atomic_write_text(snapshot_path, text)
    verify_history.atomic_write_text(path, text)


def json_text(payload: dict[str, object]) -> str:
    """Return stable JSON artifact text."""

    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def failure_section(
    failure: CheckResult,
    *,
    context_log_dir: str | None = None,
) -> list[str]:
    """Return Markdown lines for one failed check."""

    lines = [
        f"### {failure.name}",
        "",
        f"- Exit code: `{failure.exit_code}`",
        f"- Log: `{failure.log_path}`",
        "- Expansion commands:",
        *[
            f"  - `{command}`"
            for command in artifact_manifest.expansion_commands(
                failure.name, log_dir=context_log_dir
            )
        ],
    ]
    if failure.output:
        lines.extend(("", "```text", failure.output, "```"))
    lines.append("")
    return lines


def bounded_last_failure_text(text: str, config: MaintainerConfig) -> str:
    """Return LAST_FAILURE text capped by configured context budget."""

    bounded = bound_text(
        text,
        context_models.ContextBudget(
            max_chars=config.context_last_failure_budget_chars,
            max_items=config.context_max_failure_items,
        ),
    )
    if not bounded.truncated:
        return bounded.text
    preserved = preserved_expansion_footer(text, bounded.text)
    parts = [bounded.text.rstrip(), truncation_note(bounded)]
    if preserved:
        parts.append(preserved)
    return "\n\n".join(parts)


def preserved_expansion_footer(original_text: str, bounded_text: str) -> str:
    """Return command footer when truncation hides repair commands."""
    commands = [
        line.strip()
        for line in original_text.splitlines()
        if "python -m agent_maintainer context" in line and " failures " in line and line.strip()
    ]
    hidden_commands = [command for command in commands if command not in bounded_text]
    if not hidden_commands:
        return ""
    return "\n".join(("## Preserved Expansion Commands", "", *hidden_commands))


def truncation_note(bounded: context_models.BoundedText) -> str:
    """Return human-readable truncation note with exact omitted counts."""

    return (
        "... failure summary omitted "
        f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines. "
        "Full logs and artifacts remain in .verify-logs/."
    )


def rerun_command(context: RunContext) -> str:
    """Return the canonical command to rerun this verifier profile."""

    command = [
        "python3",
        "-m",
        "agent_maintainer",
        "verify",
        "--profile",
        context.profile,
        "--base-ref",
        context.base_ref,
        "--compare-branch",
        context.compare_branch,
    ]
    if context.staged:
        command.append("--staged")
    return " ".join(command)
