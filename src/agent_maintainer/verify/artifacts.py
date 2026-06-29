"""Write diagnostic artifacts for maintainer verifier runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.context import models as context_models
from agent_maintainer.context.budget import bound_text
from agent_maintainer.models import CheckResult
from agent_maintainer.verify import history as verify_history
from agent_maintainer.verify import timing as verify_timing
from agent_maintainer.verify.git_state import git_state
from agent_maintainer.verify.pr_summary import PR_SUMMARY_NAME, render_pr_summary

MANIFEST_NAME = "manifest.json"
LAST_FAILURE_NAME = "LAST_FAILURE.md"
TRUNCATION_NOTE_ALLOWANCE = 240


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
    (log_dir / PR_SUMMARY_NAME).write_text(
        render_pr_summary(log_dir=log_dir, context=context, results=results),
        encoding="utf-8",
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
    (log_dir / MANIFEST_NAME).write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


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
    (snapshot_dir / MANIFEST_NAME).write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


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
        "thresholds": threshold_snapshot(context.config),
        "checks": [
            check_payload(
                result,
                context,
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
    snapshot_path.write_text(f"{text}\n", encoding="utf-8")
    path.write_text(f"{text}\n", encoding="utf-8")


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
            for command in expansion_commands(failure.name, log_dir=context_log_dir)
        ],
    ]
    if failure.output:
        lines.extend(("", "```text", failure.output, "```"))
    lines.append("")
    return lines


def check_payload(
    result: CheckResult,
    context: RunContext,
    *,
    log_path_override: str | None = None,
    context_log_dir: str | None = None,
) -> dict[str, object]:
    """Return manifest JSON for one check result."""

    metadata = summary_metadata(result, context.config)
    log_path = log_path_override or result.log_path
    return {
        "name": result.name,
        "status": result_status(result),
        "command": list(result.command),
        "exit_code": result.exit_code,
        "log_path": log_path,
        "log_bytes": log_bytes(log_path, context.repo_root),
        "summary_chars": len(result.output),
        "summary_truncated": metadata.truncated,
        "omitted_chars": metadata.omitted_chars,
        "omitted_lines": metadata.omitted_lines,
        "expansion_commands": result_expansion_commands(result, log_dir=context_log_dir),
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "artifacts": list(result.artifact_paths),
    }


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
    return "\n\n".join((bounded.text.rstrip(), truncation_note(bounded)))


def summary_metadata(
    result: CheckResult,
    config: MaintainerConfig,
) -> context_models.BoundedText:
    """Return bounded-summary metadata for manifest output."""

    return bound_text(
        result.output,
        context_models.ContextBudget(
            max_chars=config.context_last_failure_budget_chars,
            max_items=config.context_max_failure_items,
        ),
    )


def truncation_note(bounded: context_models.BoundedText) -> str:
    """Return human-readable truncation note with exact omitted counts."""

    return (
        "... failure summary omitted "
        f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines. "
        "Full logs and artifacts remain in .verify-logs/."
    )


def expansion_commands(check_name: str, *, log_dir: str | None = None) -> list[str]:
    """Return stable placeholder context expansion commands."""

    log_dir_arg = f" --log-dir {log_dir}" if log_dir else ""
    return [
        (
            "python -m agent_maintainer context"
            f"{log_dir_arg} failures --check {check_name} --limit 20"
        ),
        f"python -m agent_maintainer context{log_dir_arg} log {check_name} --tail 120",
    ]


def result_expansion_commands(result: CheckResult, *, log_dir: str | None = None) -> list[str]:
    """Return expansion commands when result has failed."""

    if result.passed:
        return []
    return expansion_commands(result.name, log_dir=log_dir)


def log_bytes(log_path: str, repo_root: Path) -> int:
    """Return raw log size in bytes, or zero when absent."""

    if not log_path:
        return 0
    path = Path(log_path)
    if not path.is_absolute():
        path = repo_root / path
    try:
        return len(path.read_bytes())
    except OSError:
        return 0


def result_status(result: CheckResult) -> str:
    """Return a stable manifest status for a check result."""

    if result.skipped:
        return "skipped"
    if not result.passed:
        return "failed"
    if result.warning:
        return "warning"
    return "passed"


def threshold_snapshot(config: MaintainerConfig) -> dict[str, object]:
    """Return key thresholds relevant to diagnostics."""

    return {
        "coverage_fail_under": config.coverage_fail_under,
        "diff_cover_fail_under": config.diff_cover_fail_under,
        "file_length_max_physical": config.file_length_max_physical,
        "file_length_max_source": config.file_length_max_source,
        "change_warn_lines": config.change_warn_lines,
        "change_block_lines": config.change_block_lines,
        "change_warn_files": config.change_warn_files,
        "change_block_files": config.change_block_files,
        "suppression_max_new": config.suppression_max_new,
        "ruff_max_complexity": config.ruff_max_complexity,
        "pyright_type_checking_mode": config.pyright_type_checking_mode,
        "interrogate_fail_under": config.interrogate_fail_under,
    }


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
