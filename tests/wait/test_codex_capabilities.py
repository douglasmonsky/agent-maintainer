"""Tests redacted Codex rewake capability detection."""

from __future__ import annotations

from agent_waits.capabilities import (
    CODEX_BIN_ENV,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    inspect_codex_rewake_capabilities,
)


def test_capabilities_report_booleans_without_sensitive_values() -> None:
    """Capability evidence never retains thread ids or configured CLI paths."""

    thread_id = "thread-private-123"
    configured_bin = "/private/tools/codex"

    capabilities = inspect_codex_rewake_capabilities(
        {
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: thread_id,
            CODEX_BIN_ENV: configured_bin,
        },
        codex_available=True,
        sdk_available=True,
    )

    assert capabilities.feature_enabled is True
    assert capabilities.thread_context_present is True
    assert capabilities.app_server_candidate_available is True
    assert capabilities.python_sdk_available is True
    assert capabilities.automatic_visible_rewake_available is False
    assert thread_id not in repr(capabilities)
    assert configured_bin not in repr(capabilities)


def test_capabilities_distinguish_diagnostic_sdk_from_runtime_backend() -> None:
    """An installed SDK alone does not claim an implemented rewake backend."""

    capabilities = inspect_codex_rewake_capabilities(
        {CODEX_REWAKE_ENV: "1", CODEX_THREAD_ID_ENV: "thread-1"},
        codex_available=False,
        sdk_available=True,
    )

    assert capabilities.python_sdk_available is True
    assert capabilities.app_server_candidate_available is False
    assert capabilities.automatic_visible_rewake_available is False
