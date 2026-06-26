"""Documentation and config hygiene check catalog helpers."""

from __future__ import annotations

from glob import glob
from pathlib import Path

from ai_guardrails import models
from ai_guardrails.config.schema import GuardrailConfig

IGNORED_PATH_PARTS = frozenset(
    (
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".verify-logs",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "venv",
    )
)
MARKDOWNLINT_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_MARKDOWNLINT=1 or "
    "[tool.ai_guardrails].enable_markdownlint = true"
)
YAMLLINT_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_YAMLLINT=1 or "
    "[tool.ai_guardrails].enable_yamllint = true"
)
TAPLO_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_TAPLO=1 or "
    "[tool.ai_guardrails].enable_taplo = true"
)
CHECK_JSONSCHEMA_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_CHECK_JSONSCHEMA=1 or "
    "[tool.ai_guardrails].enable_check_jsonschema = true"
)


def docs_config_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build documentation and config hygiene checks."""
    return [
        markdownlint_check(config),
        yamllint_check(config),
        taplo_check(config),
        check_jsonschema_check(config),
    ]


def markdownlint_check(config: GuardrailConfig) -> models.Check:
    """Build Markdown structure lint check."""
    if not config.enable_markdownlint:
        return disabled_check("markdownlint", "markdownlint-cli2", MARKDOWNLINT_SKIP_REASON)
    paths = matching_paths(config.markdownlint_paths)
    if not paths:
        return no_files_check("markdownlint", "Markdown", config.markdownlint_paths)
    return models.Check(
        "markdownlint",
        ["markdownlint-cli2", *paths],
        models.FULL_PROFILES,
        required_executable="markdownlint-cli2",
    )


def yamllint_check(config: GuardrailConfig) -> models.Check:
    """Build YAML structure lint check."""
    if not config.enable_yamllint:
        return disabled_check("yamllint", "yamllint", YAMLLINT_SKIP_REASON)
    paths = matching_paths(config.yamllint_paths)
    if not paths:
        return no_files_check("yamllint", "YAML", config.yamllint_paths)
    return models.Check(
        "yamllint",
        ["yamllint", *paths],
        models.FULL_PROFILES,
        required_executable="yamllint",
    )


def taplo_check(config: GuardrailConfig) -> models.Check:
    """Build TOML formatting check."""
    if not config.enable_taplo:
        return disabled_check("taplo", "taplo", TAPLO_SKIP_REASON)
    paths = matching_paths(config.taplo_paths)
    if not paths:
        return no_files_check("taplo", "TOML", config.taplo_paths)
    return models.Check(
        "taplo",
        ["taplo", "fmt", "--check", *paths],
        models.FULL_PROFILES,
        required_executable="taplo",
    )


def check_jsonschema_check(config: GuardrailConfig) -> models.Check:
    """Build JSON/YAML schema validation check."""
    if not config.enable_check_jsonschema:
        return disabled_check(
            "check-jsonschema",
            "check-jsonschema",
            CHECK_JSONSCHEMA_SKIP_REASON,
        )
    if not config.check_jsonschema_args:
        return models.Check(
            "check-jsonschema",
            ["check-jsonschema"],
            models.FULL_PROFILES,
            optional_skip_reason="enabled without schema arguments; no schema contracts configured",
        )
    return models.Check(
        "check-jsonschema",
        ["check-jsonschema", *config.check_jsonschema_args],
        models.FULL_PROFILES,
        required_executable="check-jsonschema",
    )


def disabled_check(name: str, command: str, reason: str) -> models.Check:
    """Return an explicit disabled optional check."""
    return models.Check(name, [command], models.FULL_PROFILES, optional_skip_reason=reason)


def no_files_check(name: str, label: str, paths: tuple[str, ...]) -> models.Check:
    """Return an explicit no-files optional check."""
    configured = ", ".join(paths) or "<none>"
    return models.Check(
        name,
        [name],
        models.FULL_PROFILES,
        optional_skip_reason=f"enabled but no {label} files matched: {configured}",
    )


def matching_paths(patterns: tuple[str, ...]) -> tuple[str, ...]:
    """Return existing paths matched by configured file or glob patterns."""
    matches: list[str] = []
    for pattern in patterns:
        path = Path(pattern)
        if path.exists() and not ignored(path):
            matches.append(pattern)
            continue
        matches.extend(match for match in glob(pattern, recursive=True) if not ignored(Path(match)))
    return tuple(sorted(set(matches)))


def ignored(path: Path) -> bool:
    """Return whether path belongs to generated or cache output."""
    return bool(IGNORED_PATH_PARTS.intersection(path.parts))
