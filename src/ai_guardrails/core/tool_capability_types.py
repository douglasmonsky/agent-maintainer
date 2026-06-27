"""Types and constants for guardrail tool capabilities."""

from __future__ import annotations

from dataclasses import dataclass

PYTHON_PACKAGE = "python_package"
EXTERNAL_BINARY = "external_binary"
GITHUB_ACTION_ONLY = "github_action_only"
MANUAL_OPTIONAL = "manual_optional"
SUPPORTED = "supported"
MISSING = "missing"
DISABLED = "disabled"
NOT_APPLICABLE = "not_applicable"
CAPABILITY_LABELS = (
    (PYTHON_PACKAGE, "Python package command"),
    (EXTERNAL_BINARY, "external binary"),
    (GITHUB_ACTION_ONLY, "GitHub Actions-only tool"),
    (MANUAL_OPTIONAL, "manual optional tool"),
)


@dataclass(frozen=True)
class ToolCapability:
    """How a guardrail tool is installed and evaluated."""

    tool: str
    kind: str
    hint: str = ""


@dataclass(frozen=True)
class ToolState:
    """Resolved availability state for one guardrail tool."""

    tool: str
    kind: str
    state: str
    message: str
