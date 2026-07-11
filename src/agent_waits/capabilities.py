"""Redacted Codex rewake capability detection."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from shutil import which
from typing import Final

CODEX_PLATFORM: Final = "codex"
CODEX_REWAKE_ENV: Final = "AGENT_MAINTAINER_CODEX_REWAKE"
CODEX_BIN_ENV: Final = "AGENT_MAINTAINER_CODEX_BIN"
CODEX_THREAD_ID_ENV: Final = "CODEX_THREAD_ID"
CODEX_THREAD_ID_OVERRIDE_ENV: Final = "AGENT_MAINTAINER_CODEX_THREAD_ID"
CODEX_CLI_NAME: Final = "codex"
OPENAI_CODEX_PACKAGE: Final = "openai_codex"


@dataclass(frozen=True)
class CodexRewakeCapabilities:
    """Sensitive-value-free capability facts for Codex terminal rewake."""

    feature_enabled: bool
    thread_context_present: bool
    app_server_candidate_available: bool
    python_sdk_available: bool
    automatic_visible_rewake_available: bool = False


def inspect_codex_rewake_capabilities(
    env: Mapping[str, str] | None = None,
    *,
    codex_available: bool | None = None,
    sdk_available: bool | None = None,
) -> CodexRewakeCapabilities:
    """Return redacted local Codex capability facts without spawning processes."""

    current = os.environ if env is None else env
    configured_bin = current.get(CODEX_BIN_ENV, "")
    app_server_candidate = (
        bool(configured_bin or which(CODEX_CLI_NAME))
        if codex_available is None
        else codex_available
    )
    python_sdk = (
        find_spec(OPENAI_CODEX_PACKAGE) is not None if sdk_available is None else sdk_available
    )
    return CodexRewakeCapabilities(
        feature_enabled=current.get(CODEX_REWAKE_ENV) == "1",
        thread_context_present=bool(
            current.get(CODEX_THREAD_ID_OVERRIDE_ENV) or current.get(CODEX_THREAD_ID_ENV)
        ),
        app_server_candidate_available=app_server_candidate,
        python_sdk_available=python_sdk,
    )
