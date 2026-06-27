"""Static registry of known guardrail tool capabilities."""

from __future__ import annotations

from ai_guardrails.core.tool_capability_types import (
    EXTERNAL_BINARY,
    PYTHON_PACKAGE,
    ToolCapability,
)

KNOWN_CAPABILITIES = (
    ("git", ToolCapability("git", EXTERNAL_BINARY, hint="Install Git for repository checks.")),
    (
        "actionlint",
        ToolCapability(
            "actionlint",
            PYTHON_PACKAGE,
            hint="Install Python package guardrail tools from config/dev-lock.txt.",
        ),
    ),
    (
        "gitleaks",
        ToolCapability(
            "gitleaks",
            EXTERNAL_BINARY,
            hint=(
                "Install Gitleaks with the platform package manager, "
                "for example brew install gitleaks."
            ),
        ),
    ),
    (
        "osv-scanner",
        ToolCapability(
            "osv-scanner",
            EXTERNAL_BINARY,
            hint="Install OSV Scanner with the platform package manager or release binary.",
        ),
    ),
    (
        "trivy",
        ToolCapability(
            "trivy",
            EXTERNAL_BINARY,
            hint="Install Trivy with the platform package manager or release binary.",
        ),
    ),
    (
        "markdownlint-cli2",
        ToolCapability(
            "markdownlint-cli2",
            EXTERNAL_BINARY,
            hint="Install Markdownlint CLI2 from package-lock.json with npm ci.",
        ),
    ),
    (
        "taplo",
        ToolCapability(
            "taplo",
            EXTERNAL_BINARY,
            hint="Install Taplo from package-lock.json with npm ci.",
        ),
    ),
    (
        "zizmor",
        ToolCapability(
            "zizmor",
            PYTHON_PACKAGE,
            hint="Install Python package guardrail tools from config/dev-lock.txt.",
        ),
    ),
    (
        "mutmut",
        ToolCapability(
            "mutmut",
            PYTHON_PACKAGE,
            hint="Install Python package guardrail tools from config/dev-lock.txt.",
        ),
    ),
    (
        "semgrep",
        ToolCapability(
            "semgrep",
            PYTHON_PACKAGE,
            hint="Install Python package guardrail tools from config/dev-lock.txt.",
        ),
    ),
    (
        "cyclonedx-py",
        ToolCapability(
            "cyclonedx-py",
            PYTHON_PACKAGE,
            hint="Install Python package guardrail tools from config/dev-lock.txt.",
        ),
    ),
    (
        "pip-licenses",
        ToolCapability(
            "pip-licenses",
            PYTHON_PACKAGE,
            hint="Install Python package guardrail tools from config/dev-lock.txt.",
        ),
    ),
)
