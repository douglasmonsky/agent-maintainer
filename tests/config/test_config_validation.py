"""Tests Agent Maintainer config validation helpers."""

from __future__ import annotations

from agent_maintainer.config import validation


def test_unknown_keys_accepts_known_config_tables() -> None:
    """Known top-level and diagnostics keys produce no warnings."""

    raw: dict[str, object] = {
        "mode": "custom",
        "source_roots": ["src"],
        "diagnostics": {"enabled": True, "log_dir": ".verify-logs"},
    }

    assert validation.unknown_keys(raw) == ()


def test_unknown_keys_reports_top_level_and_diagnostics_typos() -> None:
    """Unsupported config keys are reported with full TOML paths."""

    raw: dict[str, object] = {
        "mode": "custom",
        "coverage_fail_nder": 90,
        "diagnostics": {"enabled": True, "lod_dir": ".verify-logs"},
    }

    assert validation.unknown_keys(raw) == (
        "tool.agent_maintainer.coverage_fail_nder",
        "tool.agent_maintainer.diagnostics.lod_dir",
    )
