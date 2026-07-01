"""Doctor setup checks that inspect local repository health."""

from __future__ import annotations

import sys
from importlib import util as importlib_util
from pathlib import Path

from agent_maintainer.core import config as maintainer_config
from agent_maintainer.core import guidance as maintainer_guidance
from agent_maintainer.core.layout import layout_failures
from agent_maintainer.doctor.support import dogfood as maintainer_doctor_dogfood
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.doctor.support import setup_policy as maintainer_doctor_policy

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
    ".verify-logs",
)

check_architecture_backend = maintainer_doctor_policy.check_architecture_backend
check_thresholds = maintainer_doctor_policy.check_thresholds
check_structure_thresholds = maintainer_doctor_policy.check_structure_thresholds
check_ratchet_baseline = maintainer_doctor_policy.check_ratchet_baseline
check_optional_gates = maintainer_doctor_policy.check_optional_gates
architecture_gate_status = maintainer_doctor_policy.architecture_gate_status
active_optional_gate_names = maintainer_doctor_policy.active_optional_gate_names
check_console_script_dogfood = maintainer_doctor_dogfood.check_console_script_dogfood
make_checks = maintainer_doctor_policy.make_checks


def check_tool_capabilities(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Check active tool capabilities through the public setup seam."""
    return maintainer_doctor_policy.check_tool_capabilities(
        repo_root,
        config,
        check_factory=make_checks,
    )


def check_source_checkout_dogfood(repo_root: Path) -> DoctorResult:
    """Report whether source checkout imports local package code."""
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
            hint="Run PYTHONPATH=src python3 -m agent_maintainer.",
        )

    resolved = Path(spec.origin).resolve()
    if resolved == expected.resolve():
        return DoctorResult("dogfood-source", OK, "Imports local src/agent_maintainer.")

    return DoctorResult(
        "dogfood-source",
        ERROR,
        f"Imports {resolved}; expected {expected.resolve()}.",
        state=maintainer_doctor_models.UNSAFE_CONFIG,
        hint="Run PYTHONPATH=src python3 -m agent_maintainer or python -m pip install -e .",
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
        hint="Verify generated duplicates before deleting them.",
    )


def duplicate_artifact_paths(repo_root: Path) -> list[str]:
    """Return suspicious duplicate artifact paths in configured generated roots."""
    matches: list[str] = []
    for root_name in DUPLICATE_ARTIFACT_ROOTS:
        root = repo_root / root_name
        matches.extend(duplicate_artifacts_in_root(repo_root, root))
    return sorted(matches)


def duplicate_artifacts_in_root(repo_root: Path, root: Path) -> list[str]:
    """Return suspicious duplicate artifacts below one generated root."""
    if not root.exists():
        return []
    return [
        path.relative_to(repo_root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and is_duplicate_artifact(path)
    ]


def is_duplicate_artifact(path: Path) -> bool:
    """Return whether path looks like an accidental duplicate artifact."""
    name = path.name.lower()
    return any(pattern in name for pattern in (" 2", " copy", " - copy"))


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


def check_tests(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Report whether required test roots are available."""
    if not config.require_tests:
        return DoctorResult(
            "tests",
            WARNING,
            "Tests are disabled because require_tests = false.",
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
            hint="Create configured test root or update test_roots.",
        )
    existing_roots = ", ".join(existing)
    return DoctorResult("tests", OK, f"Configured test roots exist: {existing_roots}")


def check_agent_guidance(
    repo_root: Path,
    config: maintainer_config.MaintainerConfig,
) -> DoctorResult:
    """Report whether generated agent guidance matches config."""
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
    """Report whether Python runtime meets verifier minimum."""
    version = sys.version_info
    detected = f"{version.major}.{version.minor}.{version.micro}"
    if (version.major, version.minor) < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        return DoctorResult(
            "python-version",
            ERROR,
            f"Python {detected}; Python {required}+ required.",
        )
    return DoctorResult("python-version", OK, f"Python {detected}")
