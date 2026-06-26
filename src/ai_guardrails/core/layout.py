"""Layout validation shared by verifier and setup diagnostics."""

from __future__ import annotations

from ai_guardrails.core.config import GuardrailConfig, any_path_exists, format_paths
from ai_guardrails.models import LOCAL_GATE_PROFILES

VALID_PYRIGHT_MODES = frozenset(("off", "basic", "standard", "strict"))


def requires_full_layout(profile: str) -> bool:
    """Return whether a verifier profile requires configured roots to exist."""

    return profile in LOCAL_GATE_PROFILES


def configured_path_failure(label: str, paths: tuple[str, ...], guidance: str = "") -> str | None:
    """Return a layout failure when none of the configured paths exists."""

    if any_path_exists(paths):
        return None
    suffix = f" {guidance}" if guidance else ""
    return f"No configured {label} exists. Configured {label}: {format_paths(paths)}.{suffix}"


def layout_failures(config: GuardrailConfig, profile: str) -> list[str]:
    """Return all layout/configuration failures for a verifier profile."""

    if not requires_full_layout(profile):
        return []

    failures = [
        configured_path_failure(
            "source root",
            config.source_roots,
            "Set [tool.ai_guardrails].source_roots, GUARDRAILS_SOURCE_ROOTS, or --source-root.",
        ),
        configured_path_failure(
            "package/static-analysis path",
            config.package_paths,
        ),
    ]

    if config.require_tests:
        failures.extend(test_layout_failures(config))
    if config.pyright_type_checking_mode not in VALID_PYRIGHT_MODES:
        valid_modes = ", ".join(sorted(VALID_PYRIGHT_MODES))
        failures.append(f"pyright_type_checking_mode must be one of: {valid_modes}")

    return [failure for failure in failures if failure is not None]


def test_layout_failures(config: GuardrailConfig) -> list[str | None]:
    """Return required test and coverage-root failures."""

    return [
        configured_path_failure(
            "test root",
            config.test_roots,
            "Create tests or set require_tests = false intentionally.",
        ),
        configured_path_failure("coverage source", config.coverage_source),
    ]
