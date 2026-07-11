"""Optional Codex rewake backend for terminal wait records."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from shutil import which
from typing import Any, Final

from agent_maintainer.wait.codex_app_server import CodexAppServerClient
from agent_maintainer.wait.handlers import continuation_prompt as handler_prompt
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry
from agent_waits.capabilities import (
    CODEX_BIN_ENV,
    CODEX_CLI_NAME,
    CODEX_PLATFORM,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    CODEX_THREAD_ID_OVERRIDE_ENV,
)
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

CODEX_APP_SERVER_TIMEOUT_ENV: Final = "AGENT_MAINTAINER_CODEX_APP_SERVER_TIMEOUT_SECONDS"
REWAKE_STATUS_DISABLED: Final = "disabled"
REWAKE_STATUS_MANUAL: Final = "ready_for_manual_resume"
REWAKE_STATUS_RESUMED: Final = "resumed"
REWAKE_STATUS_SKIPPED: Final = "skipped"
APP_SERVER_DEFAULT_TIMEOUT_SECONDS: Final = 3600.0


@dataclass(frozen=True)
class CodexRewakeResult:
    """Outcome from one optional Codex rewake attempt."""

    status: str
    detail: str
    prompt: str = ""


@dataclass(frozen=True)
class _AppServerContext:
    """Prepared Codex app-server resume context."""

    thread_id: str
    codex_bin: str
    timeout_seconds: float


class CodexRewakeBackend:
    """Resume Codex continuation when explicitly enabled."""

    def __init__(
        self,
        registry: WaitRegistry,
        *,
        env: Mapping[str, str] | None = None,
        app_server_client: Any | None = None,
    ) -> None:
        self._registry = registry
        self._env = os.environ if env is None else env
        self._app_server_client = app_server_client

    def enabled(self) -> bool:
        """Return whether Codex rewake is enabled."""

        return codex_rewake_enabled(self._env)

    def resume_if_available(self, record: WaitRecord) -> CodexRewakeResult:
        """Resume Codex thread when a supported backend is available."""

        resume_target = self._resume_context(record)
        if isinstance(resume_target, CodexRewakeResult):
            return resume_target
        prompt = continuation_prompt(record)
        try:
            self._resume_with_app_server(resume_target, prompt)
        except (OSError, RuntimeError, TimeoutError) as app_server_exc:
            return _manual_result(
                record,
                f"Codex app-server rewake failed: {app_server_exc}",
            )
        return _manual_result(
            record,
            "Codex app-server accepted continuation, but visible thread wake "
            "is not confirmed; manual resume required",
        )

    def _resume_context(
        self,
        record: WaitRecord,
    ) -> _AppServerContext | CodexRewakeResult:
        """Return prepared resume context or terminal non-resume result."""

        if not self.enabled():
            return CodexRewakeResult(REWAKE_STATUS_DISABLED, "Codex rewake disabled")
        if not _codex_record_ready(record):
            return CodexRewakeResult(REWAKE_STATUS_SKIPPED, "wait not ready for Codex")
        thread_id = codex_thread_id(self._env)
        if not thread_id:
            return _manual_result(record, "Codex thread id unavailable")
        codex_bin = codex_binary(self._env)
        if not codex_bin:
            return _manual_result(record, "Codex app-server unavailable")
        return _AppServerContext(
            thread_id=thread_id,
            codex_bin=codex_bin,
            timeout_seconds=codex_app_server_timeout_seconds(self._env),
        )

    def _resume_with_app_server(
        self,
        context: _AppServerContext,
        prompt: str,
    ) -> None:
        if not context.codex_bin:
            raise RuntimeError("Codex CLI unavailable")
        client = self._app_server_client or CodexAppServerClient(
            codex_bin=context.codex_bin,
            timeout_seconds=context.timeout_seconds,
            return_after_turn_acceptance=True,
        )
        client.resume_thread(context.thread_id, prompt)


def codex_rewake_enabled(env: Mapping[str, str]) -> bool:
    """Return whether Codex rewake is enabled."""

    return env.get(CODEX_REWAKE_ENV) == "1"


def codex_thread_id(env: Mapping[str, str]) -> str:
    """Return Codex thread metadata from explicit or inherited environment."""

    return env.get(CODEX_THREAD_ID_OVERRIDE_ENV) or env.get(CODEX_THREAD_ID_ENV, "")


def codex_binary(env: Mapping[str, str]) -> str:
    """Return Codex CLI path usable for app-server rewake."""

    configured = env.get(CODEX_BIN_ENV, "")
    if configured:
        return configured
    return which(CODEX_CLI_NAME) or ""


def codex_app_server_timeout_seconds(env: Mapping[str, str]) -> float:
    """Return bounded app-server continuation timeout."""

    raw_value = env.get(CODEX_APP_SERVER_TIMEOUT_ENV, "")
    if not raw_value:
        return APP_SERVER_DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = float(raw_value)
    except ValueError:
        return APP_SERVER_DEFAULT_TIMEOUT_SECONDS
    if parsed <= 0:
        return APP_SERVER_DEFAULT_TIMEOUT_SECONDS
    return parsed


def continuation_prompt(record: WaitRecord) -> str:
    """Return Codex continuation prompt for terminal wait."""

    return handler_prompt(record)


def codex_rewake_resumed(result: CodexRewakeResult) -> bool:
    """Return whether Codex continuation started."""

    return result.status == REWAKE_STATUS_RESUMED


def render_codex_rewake_text(
    record: WaitRecord,
    result: CodexRewakeResult,
) -> str:
    """Render compact output for successful Codex rewake."""

    return render_wait_capsule(
        WaitRepairCapsule(
            result="RESUMED",
            run_id=record.wait_id,
            details=(result.detail,),
        ),
    )


def _codex_record_ready(record: WaitRecord) -> bool:
    return record.platform == CODEX_PLATFORM and record.ready


def _manual_result(record: WaitRecord, detail: str) -> CodexRewakeResult:
    return CodexRewakeResult(
        REWAKE_STATUS_MANUAL,
        f"{detail}; manual resume: {record.resume_instruction}",
        prompt=continuation_prompt(record),
    )
