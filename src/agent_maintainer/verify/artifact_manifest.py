"""Manifest payload helpers for verifier diagnostic artifacts."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.context import models as context_models
from agent_maintainer.context.budget import bound_text
from agent_maintainer.models import CheckResult


def check_payload(
    result: CheckResult,
    repo_root: Path,
    config: MaintainerConfig,
    *,
    log_path_override: str | None = None,
    context_log_dir: str | None = None,
) -> dict[str, object]:
    """Return manifest JSON for one check result."""

    metadata = summary_metadata(result, config)
    log_path = log_path_override or result.log_path
    return {
        "name": result.name,
        "status": result_status(result),
        "command": list(result.command),
        "exit_code": result.exit_code,
        "log_path": log_path,
        "log_bytes": log_bytes(log_path, repo_root),
        "summary_chars": len(result.output),
        "summary_truncated": metadata.truncated,
        "omitted_chars": metadata.omitted_chars,
        "omitted_lines": metadata.omitted_lines,
        "expansion_commands": result_expansion_commands(result, log_dir=context_log_dir),
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "artifacts": list(result.artifact_paths),
        "artifact_sensitivity": result.artifact_sensitivity,
    }


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
        return result.skip_status or "skipped"
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
