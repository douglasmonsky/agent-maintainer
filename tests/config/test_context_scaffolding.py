"""Tests inert context, ratchet, and large-change config scaffolding."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from agent_maintainer.config import loader, schema
from agent_maintainer.core import init_template_config

EXPECTED_SCAFFOLDING_DEFAULTS = {
    "context_default_budget_chars": 12_000,
    "context_hook_budget_chars": 8_000,
    "context_last_failure_budget_chars": 16_000,
    "context_pack_budget_chars": 24_000,
    "context_large_file_threshold_lines": 800,
    "context_large_file_threshold_bytes": 250_000,
    "context_max_direct_file_read_lines": 250,
    "context_max_direct_log_read_lines": 200,
    "context_max_failure_items": 10,
    "context_max_paths_default": 50,
    "context_write_context_packs": True,
    "context_packs_local_only": True,
    "context_pack_contains_source": True,
    "context_require_outline_for_large_files": True,
    "context_compression_enabled": False,
    "context_compression_backend": "extractive",
    "context_compression_target_ratio": 0.5,
    "context_compression_require_backend": False,
    "ratchet_enabled": False,
    "ratchet_baseline_path": ".agent-maintainer/ratchet-baseline.json",
    "ratchet_guidance_path": "AGENTS.ratchet.md",
    "ratchet_target_limit": 5,
    "large_changes_enabled": False,
    "large_change_plan_dirs": (".agent-maintainer/change-plans",),
    "large_change_max_active_plans": 1,
    "large_change_allow_expired_plans": False,
    "large_change_require_required_sections": True,
    "large_change_fail_out_of_plan_paths": True,
}

PYPROJECT_OVERRIDE_EXPECTED = {
    "context_default_budget_chars": 1000,
    "context_hook_budget_chars": 1100,
    "context_last_failure_budget_chars": 1200,
    "context_pack_budget_chars": 1300,
    "context_large_file_threshold_lines": 1400,
    "context_large_file_threshold_bytes": 1500,
    "context_max_direct_file_read_lines": 160,
    "context_max_direct_log_read_lines": 170,
    "context_max_failure_items": 18,
    "context_max_paths_default": 19,
    "context_write_context_packs": False,
    "context_packs_local_only": False,
    "context_pack_contains_source": False,
    "context_require_outline_for_large_files": False,
    "context_compression_enabled": True,
    "context_compression_backend": "extractive",
    "context_compression_target_ratio": 0.25,
    "context_compression_require_backend": True,
    "ratchet_enabled": True,
    "ratchet_baseline_path": ".custom/baseline.json",
    "ratchet_guidance_path": "AGENTS.custom-ratchet.md",
    "ratchet_target_limit": 7,
    "large_changes_enabled": True,
    "large_change_plan_dirs": (".custom/change-plans", "docs/plans"),
    "large_change_max_active_plans": 2,
    "large_change_allow_expired_plans": True,
    "large_change_require_required_sections": False,
    "large_change_fail_out_of_plan_paths": False,
}

ENV_OVERRIDE_EXPECTED = {
    "context_default_budget_chars": 2000,
    "context_hook_budget_chars": 2100,
    "context_write_context_packs": False,
    "context_packs_local_only": False,
    "context_pack_contains_source": False,
    "context_compression_enabled": True,
    "context_compression_backend": "extractive",
    "context_compression_target_ratio": 0.4,
    "context_compression_require_backend": True,
    "ratchet_enabled": True,
    "ratchet_baseline_path": ".env/baseline.json",
    "ratchet_guidance_path": "AGENTS.env-ratchet.md",
    "ratchet_target_limit": 9,
    "large_changes_enabled": True,
    "large_change_plan_dirs": (".env/plans", "docs/plans"),
    "large_change_max_active_plans": 3,
    "large_change_allow_expired_plans": True,
    "large_change_require_required_sections": False,
    "large_change_fail_out_of_plan_paths": False,
}


def scaffolding_values(config: schema.MaintainerConfig) -> dict[str, object]:
    """Return direct references to upcoming-layer config fields."""

    return {
        "context_default_budget_chars": config.context_default_budget_chars,
        "context_hook_budget_chars": config.context_hook_budget_chars,
        "context_last_failure_budget_chars": config.context_last_failure_budget_chars,
        "context_pack_budget_chars": config.context_pack_budget_chars,
        "context_large_file_threshold_lines": (config.context_large_file_threshold_lines),
        "context_large_file_threshold_bytes": (config.context_large_file_threshold_bytes),
        "context_max_direct_file_read_lines": (config.context_max_direct_file_read_lines),
        "context_max_direct_log_read_lines": config.context_max_direct_log_read_lines,
        "context_max_failure_items": config.context_max_failure_items,
        "context_max_paths_default": config.context_max_paths_default,
        "context_write_context_packs": config.context_write_context_packs,
        "context_packs_local_only": config.context_packs_local_only,
        "context_pack_contains_source": config.context_pack_contains_source,
        "context_require_outline_for_large_files": (config.context_require_outline_for_large_files),
        "context_compression_enabled": config.context_compression_enabled,
        "context_compression_backend": config.context_compression_backend,
        "context_compression_target_ratio": config.context_compression_target_ratio,
        "context_compression_require_backend": (config.context_compression_require_backend),
        "ratchet_enabled": config.ratchet_enabled,
        "ratchet_baseline_path": config.ratchet_baseline_path,
        "ratchet_guidance_path": config.ratchet_guidance_path,
        "ratchet_target_limit": config.ratchet_target_limit,
        "large_changes_enabled": config.large_changes_enabled,
        "large_change_plan_dirs": config.large_change_plan_dirs,
        "large_change_max_active_plans": config.large_change_max_active_plans,
        "large_change_allow_expired_plans": config.large_change_allow_expired_plans,
        "large_change_require_required_sections": (config.large_change_require_required_sections),
        "large_change_fail_out_of_plan_paths": (config.large_change_fail_out_of_plan_paths),
    }


def test_context_scaffolding_defaults_are_stable() -> None:
    """MaintainerConfig exposes inert upcoming-layer defaults."""

    assert scaffolding_values(schema.MaintainerConfig()) == EXPECTED_SCAFFOLDING_DEFAULTS


def test_context_scaffolding_pyproject_overrides(tmp_path: Path) -> None:
    """Pyproject settings can override upcoming-layer config fields."""

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.agent_maintainer]
context_default_budget_chars = 1000
context_hook_budget_chars = 1100
context_last_failure_budget_chars = 1200
context_pack_budget_chars = 1300
context_large_file_threshold_lines = 1400
context_large_file_threshold_bytes = 1500
context_max_direct_file_read_lines = 160
context_max_direct_log_read_lines = 170
context_max_failure_items = 18
context_max_paths_default = 19
context_write_context_packs = false
context_packs_local_only = false
context_pack_contains_source = false
context_require_outline_for_large_files = false
context_compression_enabled = true
context_compression_backend = "extractive"
context_compression_target_ratio = 0.25
context_compression_require_backend = true
ratchet_enabled = true
ratchet_baseline_path = ".custom/baseline.json"
ratchet_guidance_path = "AGENTS.custom-ratchet.md"
ratchet_target_limit = 7
large_changes_enabled = true
large_change_plan_dirs = [".custom/change-plans", "docs/plans"]
large_change_max_active_plans = 2
large_change_allow_expired_plans = true
large_change_require_required_sections = false
large_change_fail_out_of_plan_paths = false
""".strip(),
        encoding="utf-8",
    )

    loaded = loader.apply_pyproject(schema.MaintainerConfig(), loader.read_pyproject(pyproject))

    loaded_values = scaffolding_values(loaded)
    for field_name, expected_value in PYPROJECT_OVERRIDE_EXPECTED.items():
        assert loaded_values[field_name] == expected_value


def test_context_scaffolding_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables can override upcoming-layer config fields."""

    envs = {
        "AGENT_MAINTAINER_CONTEXT_DEFAULT_BUDGET_CHARS": "2000",
        "AGENT_MAINTAINER_CONTEXT_HOOK_BUDGET_CHARS": "2100",
        "AGENT_MAINTAINER_CONTEXT_WRITE_CONTEXT_PACKS": "false",
        "AGENT_MAINTAINER_CONTEXT_PACKS_LOCAL_ONLY": "false",
        "AGENT_MAINTAINER_CONTEXT_PACK_CONTAINS_SOURCE": "false",
        "AGENT_MAINTAINER_CONTEXT_COMPRESSION_ENABLED": "true",
        "AGENT_MAINTAINER_CONTEXT_COMPRESSION_BACKEND": "extractive",
        "AGENT_MAINTAINER_CONTEXT_COMPRESSION_TARGET_RATIO": "0.4",
        "AGENT_MAINTAINER_CONTEXT_COMPRESSION_REQUIRE_BACKEND": "true",
        "AGENT_MAINTAINER_RATCHET_ENABLED": "true",
        "AGENT_MAINTAINER_RATCHET_BASELINE_PATH": ".env/baseline.json",
        "AGENT_MAINTAINER_RATCHET_GUIDANCE_PATH": "AGENTS.env-ratchet.md",
        "AGENT_MAINTAINER_RATCHET_TARGET_LIMIT": "9",
        "AGENT_MAINTAINER_LARGE_CHANGES_ENABLED": "true",
        "AGENT_MAINTAINER_LARGE_CHANGE_PLAN_DIRS": ".env/plans,docs/plans",
        "AGENT_MAINTAINER_LARGE_CHANGE_MAX_ACTIVE_PLANS": "3",
        "AGENT_MAINTAINER_LARGE_CHANGE_ALLOW_EXPIRED_PLANS": "true",
        "AGENT_MAINTAINER_LARGE_CHANGE_REQUIRE_REQUIRED_SECTIONS": "false",
        "AGENT_MAINTAINER_LARGE_CHANGE_FAIL_OUT_OF_PLAN_PATHS": "false",
    }
    for name, value in envs.items():
        monkeypatch.setenv(name, value)

    loaded = loader.apply_env(schema.MaintainerConfig())

    loaded_values = scaffolding_values(loaded)
    for field_name, expected_value in ENV_OVERRIDE_EXPECTED.items():
        assert loaded_values[field_name] == expected_value


def test_starter_config_contains_context_scaffolding_defaults() -> None:
    """Starter config file and initializer template expose the same defaults."""

    starter_path = Path("config/pyproject.agent-maintainer.toml")
    starter_text = starter_path.read_text(encoding="utf-8")
    template_text = init_template_config.STARTER_PYPROJECT

    assert starter_text == template_text
    parsed = tomllib.loads(starter_text)["tool"]["agent_maintainer"]

    for field_name, expected_value in EXPECTED_SCAFFOLDING_DEFAULTS.items():
        if isinstance(expected_value, tuple):
            assert tuple(parsed[field_name]) == expected_value
            continue
        assert parsed[field_name] == expected_value


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("context_default_budget_chars", -1),
        ("context_large_file_threshold_bytes", -1),
        ("context_max_failure_items", -1),
        ("ratchet_target_limit", -1),
        ("large_change_max_active_plans", -1),
    ),
)
def test_negative_scaffolding_budgets_are_rejected(field_name: str, value: int) -> None:
    """Upcoming-layer numeric budgets reject negative values."""

    with pytest.raises(TypeError, match=field_name):
        loader.apply_pyproject(schema.MaintainerConfig(), {field_name: value})


def test_invalid_context_compression_backend_is_rejected() -> None:
    """Compression backend is constrained even before compression runs."""

    with pytest.raises(TypeError, match="context_compression_backend"):
        loader.apply_pyproject(
            schema.MaintainerConfig(),
            {"context_compression_backend": "unknown"},
        )


def test_headroom_context_compression_backend_is_allowed() -> None:
    """Headroom is allowed only as an optional compression backend."""

    config = loader.apply_pyproject(
        schema.MaintainerConfig(),
        {"context_compression_backend": "headroom"},
    )

    assert config.context_compression_backend == "headroom"
