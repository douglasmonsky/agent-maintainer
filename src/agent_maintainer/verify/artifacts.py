"""Write diagnostic artifacts for maintainer verifier runs."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.context.budget import bound_text
from agent_maintainer.context.models import BoundedText, ContextBudget
from agent_maintainer.models import CheckResult

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


def utc_timestamp() -> str:
    """Return a stable UTC timestamp for JSON artifacts."""

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_run_artifacts(
    log_dir: Path,
    context: RunContext,
    results: list[CheckResult],
) -> None:
    """Write the manifest and failure note for one verifier run."""

    log_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(log_dir, context, results)
    write_last_failure(log_dir, context, [result for result in results if not result.passed])


def write_manifest(
    log_dir: Path,
    context: RunContext,
    results: list[CheckResult],
) -> None:
    """Write machine-readable metadata for one verifier run."""

    payload = {
        "version": 1,
        "generated_at": utc_timestamp(),
        "profile": context.profile,
        "base_ref": context.base_ref,
        "compare_branch": context.compare_branch,
        "staged": context.staged,
        "git": git_state(context.repo_root),
        "thresholds": threshold_snapshot(context.config),
        "checks": [check_payload(result, context) for result in results],
    }
    (log_dir / MANIFEST_NAME).write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )


def write_last_failure(
    log_dir: Path,
    context: RunContext,
    failures: list[CheckResult],
) -> None:
    """Write or clear the concise last-failure note."""

    path = log_dir / LAST_FAILURE_NAME
    if not failures:
        path.unlink(missing_ok=True)
        return
    lines = [
        "# Last Maintainer Failure",
        "",
        f"Profile: `{context.profile}`",
        f"Rerun: `{rerun_command(context)}`",
        "",
        "## Failed Checks",
        "",
    ]
    for failure in failures:
        lines.extend(failure_section(failure))
    text = bounded_last_failure_text("\n".join(lines).rstrip(), context.config)
    path.write_text(f"{text}\n", encoding="utf-8")


def failure_section(failure: CheckResult) -> list[str]:
    """Return Markdown lines for one failed check."""

    lines = [
        f"### {failure.name}",
        "",
        f"- Exit code: `{failure.exit_code}`",
        f"- Log: `{failure.log_path}`",
        "- Expansion commands:",
        *[f"  - `{command}`" for command in expansion_commands(failure.name)],
    ]
    if failure.output:
        lines.extend(("", "```text", failure.output, "```"))
    lines.append("")
    return lines


def check_payload(result: CheckResult, context: RunContext) -> dict[str, object]:
    """Return manifest JSON for one check result."""

    metadata = summary_metadata(result, context.config)
    return {
        "name": result.name,
        "status": result_status(result),
        "command": list(result.command),
        "exit_code": result.exit_code,
        "log_path": result.log_path,
        "log_bytes": log_bytes(result.log_path, context.repo_root),
        "summary_chars": len(result.output),
        "summary_truncated": metadata.truncated,
        "omitted_chars": metadata.omitted_chars,
        "omitted_lines": metadata.omitted_lines,
        "expansion_commands": result_expansion_commands(result),
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "artifacts": list(result.artifact_paths),
    }


def bounded_last_failure_text(text: str, config: MaintainerConfig) -> str:
    """Return LAST_FAILURE text capped by configured context budget."""

    bounded = bound_text(
        text,
        ContextBudget(
            max_chars=config.context_last_failure_budget_chars,
            max_items=config.context_max_failure_items,
        ),
    )
    if not bounded.truncated:
        return bounded.text
    return "\n\n".join((bounded.text.rstrip(), truncation_note(bounded)))


def summary_metadata(result: CheckResult, config: MaintainerConfig) -> BoundedText:
    """Return bounded-summary metadata for manifest output."""

    return bound_text(
        result.output,
        ContextBudget(
            max_chars=config.context_last_failure_budget_chars,
            max_items=config.context_max_failure_items,
        ),
    )


def truncation_note(bounded: BoundedText) -> str:
    """Return human-readable truncation note with exact omitted counts."""

    return (
        "... failure summary omitted "
        f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines. "
        "Full logs and artifacts remain in .verify-logs/."
    )


def expansion_commands(check_name: str) -> list[str]:
    """Return stable placeholder context expansion commands."""

    return [
        f"python -m agent_maintainer context failures --check {check_name} --limit 20",
        f"python -m agent_maintainer context log {check_name} --tail 120",
    ]


def result_expansion_commands(result: CheckResult) -> list[str]:
    """Return expansion commands when result has failed."""

    if result.passed:
        return []
    return expansion_commands(result.name)


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


def git_state(repo_root: Path) -> dict[str, object]:
    """Return compact Git metadata for the current repository."""

    return {
        "sha": git_output(repo_root, ("rev-parse", "HEAD")),
        "branch": git_output(repo_root, ("branch", "--show-current")),
        "dirty": bool(git_output(repo_root, ("status", "--short"))),
    }


def git_output(repo_root: Path, args: tuple[str, ...]) -> str:
    """Return stripped git command output, or an empty string on failure."""

    git_path = shutil.which("git")
    if git_path is None:
        return ""
    completed = subprocess.run(  # nosec B603
        [git_path, *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


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
