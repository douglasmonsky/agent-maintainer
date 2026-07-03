"""Capability model for Agent Maintainer tools and installation surfaces."""

from __future__ import annotations

import shutil
from pathlib import Path

from agent_maintainer.core.tooling import capability_types
from agent_maintainer.core.tooling.capability_registry import KNOWN_CAPABILITIES
from agent_maintainer.models import Check

PYTHON_PACKAGE = capability_types.PYTHON_PACKAGE
EXTERNAL_BINARY = capability_types.EXTERNAL_BINARY
GITHUB_ACTION_ONLY = capability_types.GITHUB_ACTION_ONLY
MANUAL_OPTIONAL = capability_types.MANUAL_OPTIONAL
SUPPORTED = capability_types.SUPPORTED
MISSING = capability_types.MISSING
DISABLED = capability_types.DISABLED
NOT_APPLICABLE = capability_types.NOT_APPLICABLE
CAPABILITY_LABELS = capability_types.CAPABILITY_LABELS
ToolCapability = capability_types.ToolCapability
ToolState = capability_types.ToolState


def capability_for_tool(tool: str) -> ToolCapability:
    """Return known capability metadata, defaulting to a Python package command."""

    for known_tool, capability in KNOWN_CAPABILITIES:
        if known_tool == tool:
            return capability
    return ToolCapability(
        tool,
        PYTHON_PACKAGE,
        hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
    )


def evaluate_tool(
    repo_root: Path,
    capability: ToolCapability,
    *,
    enabled: bool = True,
    applicable: bool = True,
) -> ToolState:
    """Resolve one tool capability to a supported, missing, or inactive state."""

    label = capability_label(capability)
    inactive = inactive_state(capability, label, enabled=enabled, applicable=applicable)
    if inactive is not None:
        return inactive
    non_local = non_local_state(capability, label)
    if non_local is not None:
        return non_local
    if executable_exists(repo_root, capability.tool):
        return ToolState(capability.tool, capability.kind, SUPPORTED, f"{label} found")
    hint = f" {capability.hint}" if capability.hint else ""
    return ToolState(capability.tool, capability.kind, MISSING, f"{label} missing.{hint}")


def inactive_state(
    capability: ToolCapability,
    label: str,
    *,
    enabled: bool,
    applicable: bool,
) -> ToolState | None:
    """Return a disabled or not-applicable state when a tool should not run."""

    if not applicable:
        return ToolState(
            capability.tool, capability.kind, NOT_APPLICABLE, f"{label} not applicable"
        )
    if not enabled:
        return ToolState(capability.tool, capability.kind, DISABLED, f"{label} disabled")
    return None


def non_local_state(capability: ToolCapability, label: str) -> ToolState | None:
    """Return supported states for tools that local bootstrap does not install."""

    if capability.kind == GITHUB_ACTION_ONLY:
        return ToolState(
            capability.tool,
            capability.kind,
            SUPPORTED,
            f"{label} configured outside local bootstrap",
        )
    if capability.kind == MANUAL_OPTIONAL:
        return ToolState(
            capability.tool,
            capability.kind,
            SUPPORTED,
            f"{label} enabled for manual use",
        )
    return None


def capability_label(capability: ToolCapability) -> str:
    """Return a user-facing capability label for one tool."""

    base = next(
        (label for kind, label in CAPABILITY_LABELS if kind == capability.kind),
        capability.kind.replace("_", " "),
    )
    return f"{base}: {capability.tool}"


def executable_exists(repo_root: Path, executable: str) -> bool:
    """Return whether an executable exists locally or on PATH."""

    local_paths = (
        repo_root / ".venv" / "bin" / executable,
        repo_root / "venv" / "bin" / executable,
        repo_root / "node_modules" / ".bin" / executable,
    )
    return any(path.exists() for path in local_paths) or shutil.which(executable) is not None


def states_for_checks(repo_root: Path, checks: list[Check]) -> list[ToolState]:
    """Return capability states for executable-backed verifier checks."""

    states: list[ToolState] = []
    for executable in sorted(required_executables(checks)):
        relevant_checks = [check for check in checks if check.required_executable == executable]
        enabled = any(check_applies(repo_root, check) for check in relevant_checks)
        states.append(evaluate_tool(repo_root, capability_for_tool(executable), enabled=enabled))
    return states


def required_executables(checks: list[Check]) -> set[str]:
    """Return unique required executables declared by checks."""

    executables: set[str] = set()
    for check in checks:
        if check.required_executable:
            executables.add(check.required_executable)
    return executables


def check_applies(repo_root: Path, check: Check) -> bool:
    """Return whether an optional check should require its executable."""

    if not check.optional_skip_reason:
        return True
    if check.name == "import-linter":
        return (repo_root / ".importlinter").exists()
    if check.name in {"tach", "tach-config"}:
        return (repo_root / "tach.toml").exists()
    if check.name in {"actionlint", "zizmor"}:
        return (repo_root / ".github" / "workflows").exists()
    return False


def local_runtime_states(repo_root: Path) -> list[ToolState]:
    """Return non-pip local runtime capability states checked by doctor."""

    return [evaluate_tool(repo_root, capability_for_tool("git"))]


def missing_executable_message(executable: str) -> str:
    """Return a capability-aware missing executable message for verifier failures."""

    capability = capability_for_tool(executable)
    label = capability_label(capability)
    hint = f" {capability.hint}" if capability.hint else ""
    return f"command not found: {executable!r}. Missing {label}.{hint}"


def bootstrap_scope_note() -> str:
    """Return a note explaining what bootstrap does not install."""

    return (
        "External binaries, GitHub-only tools, and manual optional tools are not installed by "
        "pip bootstrap; run doctor for capability status."
    )


def summarize_states(states: list[ToolState]) -> tuple[str, str]:
    """Return an aggregate state and compact message for doctor output."""

    missing = [state for state in states if state.state == MISSING]
    disabled = [state for state in states if state.state == DISABLED]
    not_applicable = [state for state in states if state.state == NOT_APPLICABLE]
    if missing:
        return MISSING, "; ".join(state.message for state in missing)
    supported_count = sum(state.state == SUPPORTED for state in states)
    return (
        SUPPORTED,
        (
            f"{supported_count} active tools found; {len(disabled)} disabled; "
            f"{len(not_applicable)} not applicable."
        ),
    )
