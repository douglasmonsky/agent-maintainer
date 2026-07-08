"""Optional Codex rewake backend for terminal wait records."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from shutil import which
from types import ModuleType
from typing import Any, Final

from agent_maintainer.wait.codex_app_server import CodexAppServerClient
from agent_maintainer.wait.handlers import continuation_prompt as handler_prompt
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

CODEX_PLATFORM: Final = "codex"
CODEX_REWAKE_ENV: Final = "AGENT_MAINTAINER_CODEX_REWAKE"
CODEX_THREAD_ID_ENV: Final = "CODEX_THREAD_ID"
CODEX_THREAD_ID_OVERRIDE_ENV: Final = "AGENT_MAINTAINER_CODEX_THREAD_ID"
CODEX_BIN_ENV: Final = "AGENT_MAINTAINER_CODEX_BIN"
CODEX_APP_SERVER_TIMEOUT_ENV: Final = "AGENT_MAINTAINER_CODEX_APP_SERVER_TIMEOUT_SECONDS"
CODEX_CLI_NAME: Final = "codex"
OPENAI_CODEX_PACKAGE: Final = "openai_codex"
REWAKE_STATUS_DISABLED: Final = "disabled"
REWAKE_STATUS_MANUAL: Final = "ready_for_manual_resume"
REWAKE_STATUS_RESUMED: Final = "resumed"
REWAKE_STATUS_SKIPPED: Final = "skipped"
SDK_RESUME_METHODS: Final = ("thread_resume", "resume_thread")
APP_SERVER_DEFAULT_TIMEOUT_SECONDS: Final = 3600.0

ImportModule = Callable[[str], ModuleType]


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
        importer: ImportModule = import_module,
        app_server_client: Any | None = None,
    ) -> None:
        self._registry = registry
        self._env = os.environ if env is None else env
        self._importer = importer
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
            fallback_result = self._resume_with_sdk_fallback(
                record,
                resume_target,
                prompt,
                app_server_exc,
            )
            if fallback_result is not None:
                return fallback_result
        self._registry.mark_resumed(record)
        return CodexRewakeResult(
            REWAKE_STATUS_RESUMED,
            "Codex continuation completed",
            prompt=prompt,
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
        if not codex_bin and _sdk_module(self._importer) is None:
            return _manual_result(record, "Codex app-server and SDK unavailable")
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
        )
        client.resume_thread(context.thread_id, prompt)

    def _resume_with_thread(
        self,
        sdk_module: ModuleType,
        thread_id: str,
        prompt: str,
    ) -> None:
        codex_factory = sdk_module.Codex
        with codex_factory() as codex:
            thread = _resume_thread(codex, thread_id)
            thread.run(prompt)

    def _resume_with_sdk_fallback(
        self,
        record: WaitRecord,
        resume_target: _AppServerContext,
        prompt: str,
        app_server_exc: BaseException,
    ) -> CodexRewakeResult | None:
        sdk_module = _sdk_module(self._importer)
        if sdk_module is None:
            return _manual_result(
                record,
                f"Codex app-server rewake failed: {app_server_exc}",
            )
        try:
            self._resume_with_thread(sdk_module, resume_target.thread_id, prompt)
        except (AttributeError, RuntimeError, TypeError) as sdk_exc:
            return _manual_result(
                record,
                f"Codex app-server rewake failed: {app_server_exc}; "
                f"Codex SDK rewake failed: {sdk_exc}",
            )
        return None


def _sdk_module(importer: ImportModule) -> ModuleType | None:
    try:
        return importer(OPENAI_CODEX_PACKAGE)
    except ImportError:
        return None


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


def _resume_thread(codex: Any, thread_id: str) -> Any:
    for method_name in SDK_RESUME_METHODS:
        try:
            method = getattr(codex, method_name)
        except AttributeError:
            continue
        return method(thread_id)
    raise RuntimeError("Codex SDK thread resume method unavailable")
