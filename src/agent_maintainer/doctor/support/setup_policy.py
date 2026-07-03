"""Doctor checks for configured maintenance policy surfaces."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_maintainer import models
from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.core import config as maintainer_config
from agent_maintainer.core.tooling import capabilities as maintainer_tool_capabilities
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.tach import tach_config_issues

DoctorResult = maintainer_doctor_models.DoctorResult
ERROR = maintainer_doctor_models.ERROR
OK = maintainer_doctor_models.OK
WARNING = maintainer_doctor_models.WARNING
CheckFactory = Callable[
    [maintainer_config.MaintainerConfig, str, str],
    list[models.Check],
]


def check_architecture_backend(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Report architecture backend config-file presence."""
    if config.architecture_tool == maintainer_config.TACH_TOOL:
        config_path = repo_root / "tach.toml"
        if not config_path.exists():
            return DoctorResult(
                "architecture-backend",
                WARNING,
                "tach configured but tach.toml missing.",
                state=maintainer_doctor_models.MISSING,
                hint="Add tach.toml or switch architecture_tool.",
            )
        return DoctorResult(
            "architecture-backend",
            OK,
            "tach active.",
            state=maintainer_doctor_models.ACTIVE,
        )

    config_path = repo_root / ".importlinter"
    if not config_path.exists():
        return DoctorResult(
            "architecture-backend",
            WARNING,
            "import-linter configured but .importlinter missing.",
            state=maintainer_doctor_models.MISSING,
            hint="Add .importlinter or switch architecture_tool.",
        )
    return DoctorResult(
        "architecture-backend",
        OK,
        "import-linter active.",
        state=maintainer_doctor_models.ACTIVE,
    )


def check_thresholds(config: maintainer_config.MaintainerConfig) -> DoctorResult:
    """Report active numeric thresholds relevant to setup health."""
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
    return DoctorResult(
        "thresholds",
        OK,
        message,
        state=maintainer_doctor_models.ACTIVE,
    )


def check_structure_thresholds(
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Report active structure cohesion thresholds and ignored paths."""
    paths = ", ".join(config.structure_paths or config.source_roots)
    ignored = ", ".join(config.structure_ignore_paths) or "none"
    block = (
        str(config.folder_file_block)
        if config.mode == maintainer_config.FRESH_STRICT_MODE
        else "disabled outside fresh-strict"
    )
    message = (
        f"paths={paths}; warn={config.folder_file_warn}; block={block}; "
        f"cluster-min={config.structure_cluster_min}; ignored={ignored}."
    )
    return DoctorResult(
        "structure-thresholds",
        OK,
        message,
        state=maintainer_doctor_models.ACTIVE,
    )


def check_ratchet_baseline(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Report stale legacy-ratchet configuration without baseline."""
    if not config.ratchet_enabled:
        return DoctorResult(
            "legacy-ratchet-baseline",
            OK,
            "legacy ratchet baseline disabled.",
            state=maintainer_doctor_models.NOT_APPLICABLE,
        )

    baseline_path = repo_root / config.ratchet_baseline_path
    if baseline_path.exists():
        return DoctorResult(
            "legacy-ratchet-baseline",
            OK,
            f"legacy ratchet baseline present: {config.ratchet_baseline_path}.",
            state=maintainer_doctor_models.ACTIVE,
        )

    return DoctorResult(
        "legacy-ratchet-baseline",
        WARNING,
        f"legacy ratchet enabled but baseline missing: {config.ratchet_baseline_path}.",
        state=maintainer_doctor_models.MISSING,
        hint=(
            "Run python3 -m agent_maintainer ratchet baseline create, "
            "or set ratchet_enabled = false."
        ),
    )


def check_tool_capabilities(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
    check_factory: CheckFactory = make_checks,
) -> DoctorResult:
    """Check active tool capabilities without conflating disabled integrations."""
    checks = check_factory(config, "HEAD", "origin/main")
    states = [
        *maintainer_tool_capabilities.states_for_checks(repo_root, checks),
        *maintainer_tool_capabilities.local_runtime_states(repo_root),
    ]
    state, message = maintainer_tool_capabilities.summarize_states(states)
    status = ERROR if state == maintainer_tool_capabilities.MISSING else OK
    result_state = (
        maintainer_doctor_models.MISSING
        if state == maintainer_tool_capabilities.MISSING
        else maintainer_doctor_models.ACTIVE
    )
    return DoctorResult("tool-capabilities", status, message, state=result_state)


def check_optional_gates(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Report whether optional hardening integrations are active."""
    architecture_name, missing = architecture_gate_status(repo_root, config)
    if not config.enable_pip_audit:
        missing.append("pip-audit disabled")
    if not config.enable_wemake:
        missing.append("wemake disabled")
    if not config.enable_interrogate:
        missing.append("interrogate disabled")

    if missing:
        result_state = maintainer_doctor_models.DISABLED
        if any("disabled" not in item for item in missing):
            result_state = maintainer_doctor_models.MISSING
        return DoctorResult(
            "optional-gates",
            WARNING,
            "; ".join(missing),
            state=result_state,
            hint="Enable gate or document why it is intentionally disabled.",
        )

    active_gate_summary = ", ".join(active_optional_gate_names(architecture_name, config))
    return DoctorResult(
        "optional-gates",
        OK,
        f"{active_gate_summary} are active.",
    )


def architecture_gate_status(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> tuple[str, list[str]]:
    """Return active architecture backend name and missing gate diagnostics."""
    if config.architecture_tool == maintainer_config.TACH_TOOL:
        return "Tach", tach_config_issues(
            repo_root,
            require_strict_root=config.mode == maintainer_config.FRESH_STRICT_MODE,
        )
    if not (repo_root / ".importlinter").exists():
        return "Import Linter", [".importlinter"]
    return "Import Linter", []


def active_optional_gate_names(
    architecture_name: str,
    config: maintainer_config.MaintainerConfig,
) -> list[str]:
    """Return active optional gate names for doctor summary output."""
    active_gates = [architecture_name, "pip-audit", "wemake", "interrogate"]
    if config.enable_sbom:
        active_gates.append("sbom")
    if config.enable_license_check:
        active_gates.append("license-check")
    return active_gates
