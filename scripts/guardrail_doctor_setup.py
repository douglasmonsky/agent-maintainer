"""Doctor checks for setup backends and active thresholds."""

from __future__ import annotations

from pathlib import Path

from scripts import guardrail_config, guardrail_doctor_models


def check_architecture_backend(
    repo_root: Path, config: guardrail_config.GuardrailConfig
) -> guardrail_doctor_models.DoctorResult:
    """Report active architecture backend and config-file presence."""

    if config.architecture_tool == guardrail_config.TACH_TOOL:
        config_path = repo_root / "tach.toml"
        if not config_path.exists():
            return guardrail_doctor_models.DoctorResult(
                "architecture-backend",
                guardrail_doctor_models.WARNING,
                "tach configured but tach.toml is missing.",
                state=guardrail_doctor_models.MISSING,
                hint="Add tach.toml or switch architecture_tool.",
            )
        return guardrail_doctor_models.DoctorResult(
            "architecture-backend",
            guardrail_doctor_models.OK,
            "tach active.",
            state=guardrail_doctor_models.ACTIVE,
        )

    config_path = repo_root / ".importlinter"
    if not config_path.exists():
        return guardrail_doctor_models.DoctorResult(
            "architecture-backend",
            guardrail_doctor_models.WARNING,
            "import-linter configured but .importlinter is missing.",
            state=guardrail_doctor_models.MISSING,
            hint="Add .importlinter or switch architecture_tool.",
        )
    return guardrail_doctor_models.DoctorResult(
        "architecture-backend",
        guardrail_doctor_models.OK,
        "import-linter active.",
        state=guardrail_doctor_models.ACTIVE,
    )


def check_thresholds(
    config: guardrail_config.GuardrailConfig,
) -> guardrail_doctor_models.DoctorResult:
    """Report active enforcement thresholds useful during setup review."""

    file_length = (
        f"{config.file_length_max_physical} physical/{config.file_length_max_source} source"
    )
    baseline = config.file_length_baseline or "disabled"
    message = (
        f"coverage={config.coverage_fail_under}%; "
        f"diff-cover={config.diff_cover_fail_under}%; "
        f"interrogate={config.interrogate_fail_under}%; "
        f"ruff-complexity={config.ruff_max_complexity}; "
        f"xenon={config.xenon_max_absolute}/{config.xenon_max_modules}/"
        f"{config.xenon_max_average}; "
        f"file-length={file_length}; file-length-baseline={baseline}."
    )
    return guardrail_doctor_models.DoctorResult(
        "thresholds",
        guardrail_doctor_models.OK,
        message,
        state=guardrail_doctor_models.ACTIVE,
    )


def check_structure_thresholds(
    config: guardrail_config.GuardrailConfig,
) -> guardrail_doctor_models.DoctorResult:
    """Report active structure cohesion thresholds and ignored paths."""

    paths = ", ".join(config.structure_paths or config.source_roots)
    ignored = ", ".join(config.structure_ignore_paths) or "none"
    block = (
        str(config.folder_file_block)
        if config.mode == guardrail_config.FRESH_STRICT_MODE
        else "disabled outside fresh-strict"
    )
    message = (
        f"paths={paths}; warn={config.folder_file_warn}; block={block}; "
        f"cluster-min={config.structure_cluster_min}; ignored={ignored}."
    )
    return guardrail_doctor_models.DoctorResult(
        "structure-thresholds",
        guardrail_doctor_models.OK,
        message,
        state=guardrail_doctor_models.ACTIVE,
    )
