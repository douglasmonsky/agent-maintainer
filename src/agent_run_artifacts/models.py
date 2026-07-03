"""Data transfer models for run artifact rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactCheckResult:
    """Check result data required by run-artifact helpers."""

    name: str
    passed: bool
    output: str = ""
    command: tuple[str, ...] = ()
    exit_code: int | None = 0
    log_path: str = ""
    warning: bool = False
    skipped: bool = False
    skip_status: str = ""
    started_at: str = ""
    ended_at: str = ""
    artifact_paths: tuple[str, ...] = ()
    artifact_sensitivity: str = "safe"


@dataclass(frozen=True)
class ArtifactConfig:
    """Maintainer config values required by run-artifact helpers."""

    coverage_fail_under: int
    diff_cover_fail_under: int
    file_length_max_physical: int
    file_length_max_source: int
    change_warn_lines: int
    change_block_lines: int
    change_warn_files: int
    change_block_files: int
    suppression_max_new: int
    ruff_max_complexity: int
    pyright_type_checking_mode: str
    interrogate_fail_under: int
    context_pack_budget_chars: int
    context_last_failure_budget_chars: int
    context_max_failure_items: int
    ratchet_enabled: bool
    ratchet_baseline_path: str
    large_changes_enabled: bool


@dataclass(frozen=True)
class ArtifactRunContext:
    """Verifier context data required by run-artifact helpers."""

    profile: str
    base_ref: str
    compare_branch: str
    staged: bool
    config: ArtifactConfig


CheckResultLike = ArtifactCheckResult
ArtifactConfigLike = ArtifactConfig
RunContextLike = ArtifactRunContext
