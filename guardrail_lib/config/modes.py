"""Built-in guardrail configuration mode presets."""

from __future__ import annotations

from dataclasses import replace

from guardrail_lib.config import schema


def apply_mode(
    config: schema.GuardrailConfig,
    mode: str,
) -> schema.GuardrailConfig:
    """Apply built-in preset defaults before explicit overrides."""

    updates: dict[str, object] = {}
    if mode == schema.LEGACY_RATCHET_MODE:
        updates = legacy_ratchet_defaults()
    elif mode == schema.FRESH_STRICT_MODE:
        updates = fresh_strict_defaults()
    return replace(config, mode=mode, **updates)


def legacy_ratchet_defaults() -> dict[str, object]:
    """Return defaults for existing repositories adopting ratchets."""

    return {
        "file_length_baseline": ".guardrails/file-length-baseline.json",
        "enable_pip_audit": False,
        "enable_wemake": False,
        "enable_interrogate": False,
    }


def fresh_strict_defaults() -> dict[str, object]:
    """Return defaults for new repositories that should block early."""

    return {
        "require_tests": True,
        "file_length_max_physical": 500,
        "file_length_max_source": 375,
        "change_warn_lines": 200,
        "change_block_lines": 600,
        "change_warn_files": 6,
        "change_block_files": 12,
        "source_without_test_change_error_profiles": ("precommit",),
        "suppression_max_new": 1,
        "ruff_max_complexity": 8,
        "enable_wemake": True,
        "enable_interrogate": True,
        "interrogate_fail_under": 80,
    }
