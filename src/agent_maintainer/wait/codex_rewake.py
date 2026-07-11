"""Optional Codex rewake backend for terminal wait records."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from shutil import which
from typing import Any, Final

from agent_maintainer.runtime_events import waiting as wait_runtime
from agent_maintainer.wait import (
    codex_app_server,
    handlers,
)
from agent_maintainer.wait import (
    registry as wait_registry,
)
from agent_waits import capabilities, constants, models, notifications

CODEX_BIN_ENV = capabilities.CODEX_BIN_ENV
CODEX_REWAKE_ENV = capabilities.CODEX_REWAKE_ENV
CODEX_THREAD_ID_ENV = capabilities.CODEX_THREAD_ID_ENV
CODEX_THREAD_ID_OVERRIDE_ENV = capabilities.CODEX_THREAD_ID_OVERRIDE_ENV
CodexAppServerClient = codex_app_server.CodexAppServerClient

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
        registry: wait_registry.WaitRegistry,
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

    def resume_if_available(
        self,
        record: wait_registry.WaitRecord,
    ) -> CodexRewakeResult:
        """Resume Codex thread when a supported backend is available."""

        resume_target = self._resume_context(record)
        if isinstance(resume_target, CodexRewakeResult):
            return resume_target
        try:
            claimed = notifications.claim_terminal_notification(
                self._registry,
                record.wait_id,
            )
        except TimeoutError:
            return _manual_result(record, "Codex notification claim is busy")
        if claimed is None:
            return CodexRewakeResult(REWAKE_STATUS_SKIPPED, "wait notification already claimed")
        prompt = continuation_prompt(claimed)
        events = _wait_events(claimed)
        wait_runtime.emit_notify_attempted(
            events,
            wait_id=claimed.wait_id,
            backend="codex-app-server",
        )
        try:
            self._resume_with_app_server(resume_target, prompt)
        except (OSError, RuntimeError, TimeoutError):
            finished = notifications.finish_terminal_notification(
                self._registry,
                record.wait_id,
                outcome=notifications.NOTIFICATION_OUTCOME_FAILED,
                failure_reason=notifications.FAILURE_APP_SERVER,
            )
            _emit_notify_failed(events, finished, notifications.FAILURE_APP_SERVER)
            return _manual_result(
                claimed,
                "Codex app-server rewake failed; details withheld",
            )
        finished = notifications.finish_terminal_notification(
            self._registry,
            record.wait_id,
            outcome=notifications.NOTIFICATION_OUTCOME_FAILED,
            failure_reason=notifications.FAILURE_VISIBLE_WAKE_UNCONFIRMED,
        )
        _emit_notify_failed(
            events,
            finished,
            notifications.FAILURE_VISIBLE_WAKE_UNCONFIRMED,
        )
        return _manual_result(
            claimed,
            "Codex app-server accepted continuation, but visible thread wake "
            "is not confirmed; manual resume required",
        )

    def _resume_context(
        self,
        record: wait_registry.WaitRecord,
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
    return which(capabilities.CODEX_CLI_NAME) or ""


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


def continuation_prompt(record: wait_registry.WaitRecord) -> str:
    """Return Codex continuation prompt for terminal wait."""

    return handlers.continuation_prompt(record)


def codex_rewake_resumed(result: CodexRewakeResult) -> bool:
    """Return whether Codex continuation started."""

    return result.status == REWAKE_STATUS_RESUMED


def render_codex_rewake_text(
    record: wait_registry.WaitRecord,
    result: CodexRewakeResult,
) -> str:
    """Render compact output for successful Codex rewake."""

    return models.render_wait_capsule(
        models.WaitRepairCapsule(
            result="RESUMED",
            run_id=record.wait_id,
            details=(result.detail,),
        ),
    )


def _codex_record_ready(record: wait_registry.WaitRecord) -> bool:
    return (
        record.platform == capabilities.CODEX_PLATFORM
        and record.status == constants.WAIT_STATUS_READY
    )


def _manual_result(
    record: wait_registry.WaitRecord,
    detail: str,
) -> CodexRewakeResult:
    return CodexRewakeResult(
        REWAKE_STATUS_MANUAL,
        f"{detail}; manual resume: {record.resume_instruction}",
        prompt=continuation_prompt(record),
    )


def _wait_events(
    record: wait_registry.WaitRecord,
) -> wait_runtime.WaitRuntimeEvents:
    return wait_runtime.WaitRuntimeEvents.create(
        target_kind=record.kind,
        target_id=record.target_id,
    )


def _emit_notify_failed(
    events: wait_runtime.WaitRuntimeEvents,
    record: wait_registry.WaitRecord,
    reason: str,
) -> None:
    if record.status == constants.WAIT_STATUS_NOTIFY_FAILED:
        wait_runtime.emit_notify_failed(
            events,
            wait_id=record.wait_id,
            reason=reason,
        )
