"""Doctor checks for context, ratchet, and planned-change health."""

from __future__ import annotations

from dataclasses import replace
from importlib import util as importlib_util
from pathlib import Path

from agent_maintainer.change_plan import parser, validation
from agent_maintainer.change_plan.models import PLAN_SUFFIX
from agent_maintainer.config import schema as config_schema
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor.support import context_artifacts, models
from agent_maintainer.ratchet import baseline, guidance, status

DoctorResult = models.DoctorResult

CONTEXT_PACK_DIR = "context"
COVERAGE_ARTIFACT_NAMES = ("coverage.json", "coverage.xml")
HEADROOM_MODULE = "headroom"
RATCHET_BASELINE_ERRORS = (OSError, ValueError, KeyError, TypeError)


def check_context_health(repo_root: Path, config: MaintainerConfig) -> list[DoctorResult]:
    """Return context, ratchet, change-plan, and compression doctor rows."""

    return [
        check_context_config(config),
        check_context_budgets(config),
        check_large_file_outline(config),
        check_context_pack_directory(repo_root, config),
        check_context_pack_upload_safety(repo_root, config),
        check_ratchet_baseline(repo_root, config),
        check_ratchet_guidance(repo_root, config),
        check_change_plans(repo_root, config),
        check_compression_backend(config),
        check_headroom_backend(config),
        check_test_intelligence_artifacts(repo_root, config),
    ]


def check_context_config(config: MaintainerConfig) -> DoctorResult:
    """Report context diagnostic configuration state."""

    if not config.diagnostic_artifacts_enabled:
        return DoctorResult(
            "context-config",
            models.OK,
            "Diagnostic artifacts disabled; context artifacts inactive.",
            state=models.DISABLED,
        )
    pack_state = "enabled" if config.context_write_context_packs else "disabled"
    message = f"artifacts={config.diagnostic_artifacts_dir}; packs={pack_state}"
    return DoctorResult("context-config", models.OK, message)


def check_context_budgets(config: MaintainerConfig) -> DoctorResult:
    """Report configured context budgets."""

    budgets = {
        "default": config.context_default_budget_chars,
        "hook": config.context_hook_budget_chars,
        "last-failure": config.context_last_failure_budget_chars,
        "pack": config.context_pack_budget_chars,
    }
    invalid = [name for name, value in budgets.items() if value <= 0]
    if invalid:
        invalid_names = ", ".join(invalid)
        return DoctorResult(
            "context-budgets",
            models.ERROR,
            f"Non-positive context budget(s): {invalid_names}.",
            state=models.UNSAFE_CONFIG,
            hint="Set positive context_*_budget_chars values.",
        )
    budget_text = ", ".join(format_budget(name, value) for name, value in budgets.items())
    return DoctorResult("context-budgets", models.OK, budget_text)


def format_budget(name: str, value: int) -> str:
    """Return one budget summary fragment."""

    return f"{name}={value}"


def check_large_file_outline(config: MaintainerConfig) -> DoctorResult:
    """Report whether large files require bounded outlines."""

    if not config.context_require_outline_for_large_files:
        return DoctorResult(
            "large-file-outline",
            models.OK,
            "Large-file outline requirement disabled.",
            state=models.DISABLED,
        )
    message = (
        f"outline required above {config.context_large_file_threshold_lines} lines "
        f"or {config.context_large_file_threshold_bytes} bytes"
    )
    return DoctorResult("large-file-outline", models.OK, message)


def check_context_pack_directory(repo_root: Path, config: MaintainerConfig) -> DoctorResult:
    """Report context pack artifact directory presence."""

    if not config.context_write_context_packs:
        return DoctorResult(
            "context-pack-directory",
            models.OK,
            "Context pack writing disabled.",
            state=models.DISABLED,
        )
    pack_dir = repo_root / config.diagnostic_artifacts_dir / CONTEXT_PACK_DIR
    if pack_dir.exists():
        return DoctorResult("context-pack-directory", models.OK, pack_dir.as_posix())
    return DoctorResult(
        "context-pack-directory",
        models.OK,
        f"{pack_dir.as_posix()} has not been created yet.",
        state=models.MISSING,
        hint="Run a verifier profile or context pack command to create it.",
    )


def check_context_pack_upload_safety(
    repo_root: Path,
    config: MaintainerConfig,
) -> DoctorResult:
    """Report whether workflows upload local-only context packs unsafely."""

    result = context_artifacts.check_context_pack_upload_policy(repo_root, config)
    return replace(result, name="context-pack-upload-safety")


def check_ratchet_baseline(repo_root: Path, config: MaintainerConfig) -> DoctorResult:
    """Report ratchet baseline presence and stale status."""

    if not config.ratchet_enabled:
        return DoctorResult(
            "ratchet-baseline",
            models.OK,
            "Ratchet disabled.",
            state=models.DISABLED,
        )
    baseline_path = repo_root / config.ratchet_baseline_path
    if not baseline_path.exists():
        return DoctorResult(
            "ratchet-baseline",
            models.OK,
            f"{baseline_path.as_posix()} missing.",
            state=models.MISSING,
            hint="Run python -m agent_maintainer ratchet baseline when ready.",
        )
    try:
        report = status.status_report(baseline.read_baseline(baseline_path), base_ref="HEAD")
    except RATCHET_BASELINE_ERRORS as exc:
        return DoctorResult(
            "ratchet-baseline",
            models.ERROR,
            f"Ratchet baseline unreadable: {exc}",
            state=models.UNSAFE_CONFIG,
        )
    if report.stale_reasons:
        reason_text = "; ".join(report.stale_reasons)
        return DoctorResult(
            "ratchet-baseline",
            models.WARNING,
            reason_text,
            state=models.UNSAFE_CONFIG,
            hint="Refresh ratchet baseline after reviewing stale reasons.",
        )
    counts = report.counts()
    return DoctorResult("ratchet-baseline", models.OK, f"active; counts={counts}")


def check_ratchet_guidance(repo_root: Path, config: MaintainerConfig) -> DoctorResult:
    """Report ratchet guidance sidecar freshness."""

    if not config.ratchet_enabled:
        return DoctorResult(
            "ratchet-guidance",
            models.OK,
            "Ratchet disabled.",
            state=models.DISABLED,
        )
    guidance_path = repo_root / config.ratchet_guidance_path
    if not guidance_path.exists():
        return DoctorResult(
            "ratchet-guidance",
            models.ERROR,
            f"{guidance_path.as_posix()} missing.",
            state=models.MISSING,
            hint="Run python -m agent_maintainer guidance.",
        )
    expected = guidance.render_ratchet_guidance(config)
    if guidance_path.read_text(encoding="utf-8") != expected:
        return DoctorResult(
            "ratchet-guidance",
            models.ERROR,
            f"{guidance_path.as_posix()} is stale.",
            state=models.UNSAFE_CONFIG,
            hint="Run python -m agent_maintainer guidance.",
        )
    return DoctorResult("ratchet-guidance", models.OK, f"{guidance_path.as_posix()} current.")


def check_change_plans(repo_root: Path, config: MaintainerConfig) -> DoctorResult:
    """Report cohesive change-plan configuration and validity."""

    paths = change_plan_paths(repo_root, config)
    issues = change_plan_issues(paths)
    if issues:
        return DoctorResult(
            "change-plans",
            models.ERROR,
            "; ".join(issues),
            state=models.UNSAFE_CONFIG,
            hint="Fix invalid files in configured large_change_plan_dirs.",
        )
    if paths:
        return DoctorResult("change-plans", models.OK, f"{len(paths)} valid plan(s).")
    if config.large_changes_enabled:
        return DoctorResult(
            "change-plans",
            models.WARNING,
            "Large changes enabled but no change plans found.",
            state=models.MISSING,
            hint="Create a plan with python -m agent_maintainer change-plan new.",
        )
    return DoctorResult(
        "change-plans",
        models.OK,
        "Large changes disabled; no active plans.",
        state=models.DISABLED,
    )


def change_plan_paths(repo_root: Path, config: MaintainerConfig) -> tuple[Path, ...]:
    """Return configured cohesive change-plan markdown files."""

    found: list[Path] = []
    for plan_dir_name in config.large_change_plan_dirs:
        plan_dir = repo_root / plan_dir_name
        if plan_dir.exists():
            found.extend(sorted(plan_dir.glob(f"*{PLAN_SUFFIX}")))
    return tuple(found)


def change_plan_issues(paths: tuple[Path, ...]) -> list[str]:
    """Return parse and validation issues for plan files."""

    issues: list[str] = []
    for path in paths:
        try:
            plan = parser.parse_plan(path)
        except (OSError, parser.PlanParseError) as exc:
            issues.append(f"{path.as_posix()}: {exc}")
            continue
        issues.extend(f"{issue.path}: {issue.message}" for issue in validation.validate_plan(plan))
    return issues


def check_compression_backend(config: MaintainerConfig) -> DoctorResult:
    """Report context compression backend config."""

    if not config.context_compression_enabled:
        return DoctorResult(
            "compression-backend",
            models.OK,
            "Context compression disabled.",
            state=models.DISABLED,
        )
    backend = config.context_compression_backend
    if backend not in config_schema.VALID_CONTEXT_COMPRESSION_BACKENDS:
        return DoctorResult(
            "compression-backend",
            models.ERROR,
            f"Unsupported context compression backend: {backend}.",
            state=models.UNSAFE_CONFIG,
        )
    required = "required" if config.context_compression_require_backend else "optional"
    return DoctorResult("compression-backend", models.OK, f"{backend} active ({required}).")


def check_headroom_backend(config: MaintainerConfig) -> DoctorResult:
    """Report optional Headroom backend availability."""

    headroom_enabled = (
        config.context_compression_enabled
        and config.context_compression_backend == config_schema.HEADROOM_COMPRESSION_BACKEND
    )
    if not headroom_enabled:
        return DoctorResult(
            "headroom-backend",
            models.OK,
            "Headroom compression not configured.",
            state=models.NOT_APPLICABLE,
        )
    if importlib_util.find_spec(HEADROOM_MODULE) is not None:
        return DoctorResult("headroom-backend", models.OK, "Headroom import available.")
    status_value = models.ERROR if config.context_compression_require_backend else models.WARNING
    return DoctorResult(
        "headroom-backend",
        status_value,
        "Headroom compression backend is configured but not installed.",
        state=models.MISSING,
        hint='Install with python -m pip install "agent-maintainer[compression]".',
    )


def check_test_intelligence_artifacts(
    repo_root: Path,
    config: MaintainerConfig,
) -> DoctorResult:
    """Report coverage artifacts used by test intelligence."""

    artifact_paths = test_intelligence_artifact_paths(repo_root, config)
    existing = [path for path in artifact_paths if path.exists()]
    if existing:
        names = ", ".join(path.as_posix() for path in existing)
        return DoctorResult("test-intelligence-artifacts", models.OK, names)
    return DoctorResult(
        "test-intelligence-artifacts",
        models.WARNING,
        "No coverage artifacts found for test intelligence.",
        state=models.MISSING,
        hint="Run full or ci verification to refresh coverage artifacts.",
    )


def test_intelligence_artifact_paths(
    repo_root: Path,
    config: MaintainerConfig,
) -> tuple[Path, ...]:
    """Return candidate coverage artifact paths for test intelligence."""

    log_dir = repo_root / config.diagnostic_artifacts_dir
    return tuple(
        path for name in COVERAGE_ARTIFACT_NAMES for path in (repo_root / name, log_dir / name)
    )
