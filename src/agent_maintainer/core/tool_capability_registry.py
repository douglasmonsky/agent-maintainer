"""Static registry of known maintainer tool capabilities."""

from __future__ import annotations

from agent_maintainer.core.tool_capability_types import (
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
            hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
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
        "node",
        ToolCapability(
            "node",
            EXTERNAL_BINARY,
            hint="Install Node.js with your platform package manager or version manager.",
        ),
    ),
    (
        "npm",
        ToolCapability(
            "npm",
            EXTERNAL_BINARY,
            hint="Install Node.js/npm, then install project packages with npm install or npm ci.",
        ),
    ),
    (
        "npx",
        ToolCapability(
            "npx",
            EXTERNAL_BINARY,
            hint="Install Node.js/npm, then install project packages with npm install or npm ci.",
        ),
    ),
    (
        "pnpm",
        ToolCapability(
            "pnpm",
            EXTERNAL_BINARY,
            hint="Install pnpm and project packages before running TypeScript checks.",
        ),
    ),
    (
        "yarn",
        ToolCapability(
            "yarn",
            EXTERNAL_BINARY,
            hint="Install Yarn and project packages before running TypeScript checks.",
        ),
    ),
    (
        "bun",
        ToolCapability(
            "bun",
            EXTERNAL_BINARY,
            hint="Install Bun and project packages before running TypeScript checks.",
        ),
    ),
    (
        "eslint",
        ToolCapability(
            "eslint",
            EXTERNAL_BINARY,
            hint="Install project Node dependencies so eslint is available.",
        ),
    ),
    (
        "tsc",
        ToolCapability(
            "tsc",
            EXTERNAL_BINARY,
            hint="Install TypeScript in project Node dependencies so tsc is available.",
        ),
    ),
    (
        "vitest",
        ToolCapability(
            "vitest",
            EXTERNAL_BINARY,
            hint="Install project Node dependencies so vitest is available.",
        ),
    ),
    (
        "jest",
        ToolCapability(
            "jest",
            EXTERNAL_BINARY,
            hint="Install project Node dependencies so jest is available.",
        ),
    ),
    (
        "biome",
        ToolCapability(
            "biome",
            EXTERNAL_BINARY,
            hint="Install project Node dependencies so Biome is available.",
        ),
    ),
    (
        "prettier",
        ToolCapability(
            "prettier",
            EXTERNAL_BINARY,
            hint="Install project Node dependencies so Prettier is available.",
        ),
    ),
    (
        "go",
        ToolCapability(
            "go",
            EXTERNAL_BINARY,
            hint="Install the Go toolchain with your platform package manager.",
        ),
    ),
    (
        "gofmt",
        ToolCapability(
            "gofmt",
            EXTERNAL_BINARY,
            hint="Install the Go toolchain; gofmt ships with Go.",
        ),
    ),
    (
        "golangci-lint",
        ToolCapability(
            "golangci-lint",
            EXTERNAL_BINARY,
            hint="Install golangci-lint with your Go or platform package manager.",
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
            hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
        ),
    ),
    (
        "mutmut",
        ToolCapability(
            "mutmut",
            PYTHON_PACKAGE,
            hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
        ),
    ),
    (
        "semgrep",
        ToolCapability(
            "semgrep",
            PYTHON_PACKAGE,
            hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
        ),
    ),
    (
        "cyclonedx-py",
        ToolCapability(
            "cyclonedx-py",
            PYTHON_PACKAGE,
            hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
        ),
    ),
    (
        "pip-licenses",
        ToolCapability(
            "pip-licenses",
            PYTHON_PACKAGE,
            hint="Install Python package Agent Maintainer tools from config/dev-lock.txt.",
        ),
    ),
)
