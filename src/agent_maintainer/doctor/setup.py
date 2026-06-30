"""Doctor checks for setup backends and active thresholds."""

from __future__ import annotations

import re
import sys
from importlib import util as importlib_util
from pathlib import Path

from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.core import config as maintainer_config
from agent_maintainer.core import guidance as maintainer_guidance
from agent_maintainer.core import tool_capabilities as maintainer_tool_capabilities
from agent_maintainer.core.layout import layout_failures
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.tach import tach_config_issues

DoctorResult = maintainer_doctor_models.DoctorResult
ERROR = maintainer_doctor_models.ERROR
OK = maintainer_doctor_models.OK
WARNING = maintainer_doctor_models.WARNING

MIN_PYTHON = (3, 11)
DUPLICATE_ARTIFACT_ROOTS = (
    "src",
    "tests",
    ".agent-maintainer",
    ".codex/hooks",
    ".claude/hooks",
)
DUPLICATE_ARTIFACT_PATTERN = re.compile(r" \d+(?:\.[^.]+)?$")


def check_architecture_backend(
    repo_root: Path, config: maintainer_config.MaintainerConfig
) -> maintainer_doctor_models.DoctorResult:
    """Report active architecture backend and config-file presence."""

    if config.architecture_tool == maintainer_config.TACH_TOOL:
        config_path = repo_root / "tach.toml"
        if not config_path.exists():
            return maintainer_doctor_models.DoctorResult(
                "architecture-backend",
                maintainer_doctor_models.WARNING,
                "tach configured but tach.toml is missing.",
                state=maintainer_doctor_models.MISSING,
                hint="Add tach.toml or switch architecture_tool.",
            )
        return maintainer_doctor_models.DoctorResult(
            "architecture-backend",
            maintainer_doctor_models.OK,
            "tach active.",
            state=maintainer_doctor_models.ACTIVE,
        )

    config_path = repo_root / ".importlinter"
    if not config_path.exists():
        return maintainer_doctor_models.DoctorResult(
            "architecture-backend",
            maintainer_doctor_models.WARNING,
            "import-linter configured but .importlinter is missing.",
            state=maintainer_doctor_models.MISSING,
            hint="Add .importlinter or switch architecture_tool.",
        )
    return maintainer_doctor_models.DoctorResult(
        "architecture-backend",
        maintainer_doctor_models.OK,
        "import-linter active.",
        state=maintainer_doctor_models.ACTIVE,
    )


def check_thresholds(
    config: maintainer_config.MaintainerConfig,
) -> maintainer_doctor_models.DoctorResult:
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
    return maintainer_doctor_models.DoctorResult(
        "thresholds",
        maintainer_doctor_models.OK,
        message,
        state=maintainer_doctor_models.ACTIVE,
    )


def check_structure_thresholds(
    config: maintainer_config.MaintainerConfig,
) -> maintainer_doctor_models.DoctorResult:
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
    return maintainer_doctor_models.DoctorResult(
        "structure-thresholds",
        maintainer_doctor_models.OK,
        message,
        state=maintainer_doctor_models.ACTIVE,
    )


def check_tool_capabilities(
    repo_root: Path, config: maintainer_config.MaintainerConfig
) -> DoctorResult:
    """Check active tool capabilities without conflating disabled integrations."""

    checks = make_checks(config, "HEAD", "origin/main")
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


def check_source_checkout_dogfood(repo_root: Path) -> DoctorResult:
    """Report whether this source checkout imports local package code."""

    expected = repo_root / "src" / "agent_maintainer" / "__init__.py"
    if not expected.exists():
        return DoctorResult(
            "dogfood-source",
            OK,
            "No local src/agent_maintainer package.",
            state=maintainer_doctor_models.NOT_APPLICABLE,
        )

    spec = importlib_util.find_spec("agent_maintainer")
    if spec is None or spec.origin is None:
        return DoctorResult(
            "dogfood-source",
            ERROR,
            "Cannot resolve active agent_maintainer import.",
            state=maintainer_doctor_models.MISSING,
            hint="Run with PYTHONPATH=src python3 -m agent_maintainer.",
        )

    resolved = Path(spec.origin).resolve()
    if resolved == expected.resolve():
        return DoctorResult("dogfood-source", OK, "Imports local src/agent_maintainer.")

    return DoctorResult(
        "dogfood-source",
        ERROR,
        f"Imports {resolved}; expected {expected.resolve()}.",
        state=maintainer_doctor_models.UNSAFE_CONFIG,
        hint=(
            "Run with PYTHONPATH=src python3 -m agent_maintainer or reinstall "
            "editable with python -m pip install -e ."
        ),
    )


def check_duplicate_generated_artifacts(repo_root: Path) -> DoctorResult:
    """Report likely macOS-style duplicate artifacts in generated/source roots."""

    matches = duplicate_artifact_paths(repo_root)
    if not matches:
        return DoctorResult("duplicate-artifacts", OK, "No duplicate artifacts found.")

    preview = ", ".join(matches[:5])
    hidden = len(matches) - 5
    suffix = f"; {hidden} more" if hidden > 0 else ""
    return DoctorResult(
        "duplicate-artifacts",
        WARNING,
        f"Suspicious duplicate artifacts: {preview}{suffix}.",
        state=maintainer_doctor_models.UNSAFE_CONFIG,
        hint="Verify they are generated duplicates before deleting them.",
    )


def duplicate_artifact_paths(repo_root: Path) -> list[str]:
    """Return suspicious duplicate artifact paths under checked roots."""

    matches: list[str] = []
    for root_name in DUPLICATE_ARTIFACT_ROOTS:
        root = repo_root / root_name
        if root.exists():
            matches.extend(duplicate_artifacts_in_root(repo_root, root))
    return sorted(matches)


def duplicate_artifacts_in_root(repo_root: Path, root: Path) -> list[str]:
    """Return suspicious duplicate artifact paths under one root."""

    matches: list[str] = []
    for path in root.rglob("*"):
        if path.is_file() and DUPLICATE_ARTIFACT_PATTERN.search(path.name):
            matches.append(path.relative_to(repo_root).as_posix())
    return matches


def check_layout(config: maintainer_config.MaintainerConfig) -> DoctorResult:
    """Validate configured source, package, test, and coverage roots."""

    failures = layout_failures(config, "full")
    if failures:
        return DoctorResult(
            "configured-roots",
            ERROR,
            "; ".join(failures),
            state=maintainer_doctor_models.MISSING,
            hint="Create missing roots or update [tool.agent_maintainer] paths.",
        )
    source_roots = maintainer_config.format_paths(config.source_roots)
    test_roots = maintainer_config.format_paths(config.test_roots)
    return DoctorResult("configured-roots", OK, f"sources={source_roots}; tests={test_roots}")


def check_tests(repo_root: Path, config: maintainer_config.MaintainerConfig) -> DoctorResult:
    """Report whether tests are required and available."""

    if not config.require_tests:
        return DoctorResult(
            "tests",
            WARNING,
            "Tests are disabled with require_tests = false.",
            state=maintainer_doctor_models.DISABLED,
        )
    existing = [path for path in config.test_roots if (repo_root / path).exists()]
    if not existing:
        test_roots = maintainer_config.format_paths(config.test_roots)
        return DoctorResult(
            "tests",
            ERROR,
            f"No configured test roots exist: {test_roots}",
            state=maintainer_doctor_models.MISSING,
            hint="Create the configured test root or update test_roots.",
        )
    existing_roots = ", ".join(existing)
    return DoctorResult("tests", OK, f"Configured test roots exist: {existing_roots}")


def check_optional_gates(
    repo_root: Path, config: maintainer_config.MaintainerConfig
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
            hint="Enable the gate or document why it is intentionally disabled.",
        )
    active_gate_summary = ", ".join(active_optional_gate_names(architecture_name, config))
    return DoctorResult(
        "optional-gates",
        OK,
        f"{active_gate_summary} are active.",
    )


def architecture_gate_status(
    repo_root: Path, config: maintainer_config.MaintainerConfig
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
    architecture_name: str, config: maintainer_config.MaintainerConfig
) -> list[str]:
    """Return active optional gate names for doctor summary output."""

    active_gates = [architecture_name, "pip-audit", "wemake", "interrogate"]
    if config.enable_sbom:
        active_gates.append("sbom")
    if config.enable_license_check:
        active_gates.append("license-check")
    return active_gates


def check_agent_guidance(
    repo_root: Path, config: maintainer_config.MaintainerConfig
) -> DoctorResult:
    """Report whether generated agent guidance matches current config."""

    state = maintainer_guidance.guidance_state(repo_root, config)
    if state.status == "current":
        return DoctorResult("agent-guidance", OK, state.message)
    status = ERROR if config.mode == maintainer_config.FRESH_STRICT_MODE else WARNING
    result_state = (
        maintainer_doctor_models.UNSAFE_CONFIG
        if state.status == "stale"
        else maintainer_doctor_models.MISSING
    )
    return DoctorResult(
        "agent-guidance",
        status,
        state.message,
        state=result_state,
        hint="Run python3 -m agent_maintainer guidance.",
    )


def check_python_version() -> DoctorResult:
    """Check that the active Python runtime satisfies the verifier minimum."""

    version = sys.version_info
    detected = f"{version.major}.{version.minor}.{version.micro}"
    if (version.major, version.minor) < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        return DoctorResult(
            "python-version",
            ERROR,
            f"Python {detected}; Python {required}+ is required.",
        )
    return DoctorResult("python-version", OK, f"Python {detected}")
