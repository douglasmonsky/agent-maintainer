"""Adapters from verifier product models to run-artifact DTOs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.models import CheckResult
from agent_run_artifacts import models as artifact_models

ArtifactConfig = artifact_models.ArtifactConfig


@dataclass(frozen=True)
class PartialRunContext:
    """Identity required to aggregate one grouped verifier run."""

    group: str
    required_groups: tuple[str, ...]
    identity: Mapping[str, object]


@dataclass(frozen=True)
class RunContext:
    """Context shared by checks in one verifier run."""

    repo_root: Path
    profile: str
    base_ref: str
    compare_branch: str
    staged: bool
    config: MaintainerConfig
    run_id: str
    partial: PartialRunContext | None = None


def artifact_config(config: MaintainerConfig) -> artifact_models.ArtifactConfig:
    """Return run-artifact config DTO from maintainer config."""

    return artifact_models.ArtifactConfig(
        coverage_fail_under=config.coverage_fail_under,
        diff_cover_fail_under=config.diff_cover_fail_under,
        file_length_max_physical=config.file_length_max_physical,
        file_length_max_source=config.file_length_max_source,
        change_warn_lines=config.change_warn_lines,
        change_block_lines=config.change_block_lines,
        change_warn_files=config.change_warn_files,
        change_block_files=config.change_block_files,
        suppression_max_new=config.suppression_max_new,
        ruff_max_complexity=config.ruff_max_complexity,
        pyright_type_checking_mode=config.pyright_type_checking_mode,
        interrogate_fail_under=config.interrogate_fail_under,
        context_pack_budget_chars=config.context_pack_budget_chars,
        context_last_failure_budget_chars=config.context_last_failure_budget_chars,
        context_max_failure_items=config.context_max_failure_items,
        ratchet_enabled=config.ratchet_enabled,
        ratchet_baseline_path=config.ratchet_baseline_path,
        large_changes_enabled=config.large_changes_enabled,
    )


def artifact_run_context(context: RunContext) -> artifact_models.ArtifactRunContext:
    """Return run-artifact context DTO from verifier context."""

    return artifact_models.ArtifactRunContext(
        profile=context.profile,
        base_ref=context.base_ref,
        compare_branch=context.compare_branch,
        staged=context.staged,
        config=artifact_config(context.config),
    )


def artifact_check_result(result: CheckResult) -> artifact_models.ArtifactCheckResult:
    """Return run-artifact check DTO from verifier result."""

    return artifact_models.ArtifactCheckResult(
        name=result.name,
        passed=result.passed,
        output=result.output,
        command=tuple(result.command),
        exit_code=result.exit_code,
        log_path=result.log_path,
        warning=result.warning,
        skipped=result.skipped,
        skip_status=result.skip_status,
        started_at=result.started_at,
        ended_at=result.ended_at,
        artifact_paths=tuple(result.artifact_paths),
        artifact_sensitivity=result.artifact_sensitivity,
    )


def artifact_check_results(
    results: list[CheckResult],
) -> tuple[artifact_models.ArtifactCheckResult, ...]:
    """Return run-artifact check DTOs from verifier results."""

    return tuple(artifact_check_result(result) for result in results)
