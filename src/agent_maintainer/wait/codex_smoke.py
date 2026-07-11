"""Explicit, redacted Codex app-server smoke harness."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from shutil import which
from typing import Final, Protocol

from agent_maintainer.wait.codex_app_server import CodexAppServerClient
from agent_waits.capabilities import (
    CODEX_BIN_ENV,
    CODEX_CLI_NAME,
    CODEX_THREAD_ID_ENV,
    CODEX_THREAD_ID_OVERRIDE_ENV,
)

CODEX_SMOKE_TURN_ENV: Final = "AGENT_MAINTAINER_CODEX_REWAKE_SMOKE_TURN"
CODEX_SMOKE_PROMPT: Final = "Reply with exactly: agent-maintainer Codex rewake smoke complete."
SMOKE_MODE_READ_ONLY: Final = "read-only"
SMOKE_MODE_TURN: Final = "turn"
SMOKE_STATUS_PASS: Final = "PASS"
SMOKE_STATUS_ERROR: Final = "ERROR"
DEFAULT_SMOKE_TIMEOUT_SECONDS: Final = 30.0


class SmokeClient(Protocol):
    """App-server operations used by the smoke harness."""

    def probe_thread(self, thread_id: str) -> None:
        """Run a read-only thread probe."""

    def resume_thread(self, thread_id: str, prompt: str) -> None:
        """Start one explicitly authorized smoke turn."""


SmokeClientFactory = Callable[..., SmokeClient]


@dataclass(frozen=True)
class CodexSmokeResult:
    """Redacted outcome from one explicit app-server smoke."""

    status: str
    mode: str
    detail: str
    exit_code: int = 0

    def as_dict(self) -> dict[str, object]:
        """Return stable machine-readable smoke output."""

        return {
            "status": self.status,
            "mode": self.mode,
            "detail": self.detail,
            "exit_code": self.exit_code,
        }


def run_codex_smoke(
    *,
    start_turn: bool,
    timeout_seconds: float = DEFAULT_SMOKE_TIMEOUT_SECONDS,
    env: Mapping[str, str] | None = None,
    client_factory: SmokeClientFactory = CodexAppServerClient,
) -> CodexSmokeResult:
    """Run read-only probing or one explicitly gated real Codex turn."""

    current = os.environ if env is None else env
    mode = SMOKE_MODE_TURN if start_turn else SMOKE_MODE_READ_ONLY
    if start_turn and current.get(CODEX_SMOKE_TURN_ENV) != "1":
        return CodexSmokeResult(
            SMOKE_STATUS_ERROR,
            mode,
            f"Set {CODEX_SMOKE_TURN_ENV}=1 to authorize one model turn.",
            exit_code=2,
        )
    thread_id = current.get(CODEX_THREAD_ID_OVERRIDE_ENV) or current.get(
        CODEX_THREAD_ID_ENV,
        "",
    )
    if not thread_id:
        return _smoke_error(mode, "Codex thread context is unavailable.")
    codex_bin = current.get(CODEX_BIN_ENV) or which(CODEX_CLI_NAME) or ""
    if not codex_bin:
        return _smoke_error(mode, "Codex CLI app-server candidate is unavailable.")
    client = client_factory(
        codex_bin=codex_bin,
        timeout_seconds=timeout_seconds,
    )
    try:
        if start_turn:
            client.resume_thread(thread_id, CODEX_SMOKE_PROMPT)
        else:
            client.probe_thread(thread_id)
    except (OSError, RuntimeError, TimeoutError) as exc:
        error_type = type(exc).__name__
        return _smoke_error(
            mode,
            f"Codex app-server smoke failed ({error_type}); details withheld.",
        )
    detail = (
        "Authorized Codex app-server turn completed."
        if start_turn
        else "Read-only Codex app-server probe passed."
    )
    return CodexSmokeResult(SMOKE_STATUS_PASS, mode, detail)


def render_codex_smoke_text(result: CodexSmokeResult) -> str:
    """Render compact human-readable smoke output."""

    return f"Result: {result.status}\nMode: {result.mode}\n{result.detail}"


def render_codex_smoke_json(result: CodexSmokeResult) -> str:
    """Render stable JSON smoke output."""

    return json.dumps(result.as_dict(), sort_keys=True)


def _smoke_error(mode: str, detail: str) -> CodexSmokeResult:
    return CodexSmokeResult(SMOKE_STATUS_ERROR, mode, detail, exit_code=1)
