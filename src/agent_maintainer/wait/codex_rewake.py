"""Optional Codex SDK rewake backend for terminal wait records."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Any, Final

from agent_maintainer.wait.handlers import continuation_prompt as handler_prompt
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry
from agent_waits.models import WaitRepairCapsule, render_wait_capsule

CODEX_PLATFORM: Final = "codex"
CODEX_REWAKE_ENV: Final = "AGENT_MAINTAINER_CODEX_REWAKE"
CODEX_THREAD_ID_ENV: Final = "CODEX_THREAD_ID"
CODEX_THREAD_ID_OVERRIDE_ENV: Final = "AGENT_MAINTAINER_CODEX_THREAD_ID"
OPENAI_CODEX_PACKAGE: Final = "openai_codex"
REWAKE_STATUS_DISABLED: Final = "disabled"
REWAKE_STATUS_MANUAL: Final = "ready_for_manual_resume"
REWAKE_STATUS_RESUMED: Final = "resumed"
REWAKE_STATUS_SKIPPED: Final = "skipped"
SDK_RESUME_METHODS: Final = ("thread_resume", "resume_thread")

ImportModule = Callable[[str], ModuleType]


@dataclass(frozen=True)
class CodexRewakeResult:
    """Outcome from one optional Codex rewake attempt."""

    status: str
    detail: str
    prompt: str = ""


@dataclass(frozen=True)
class _RewakeContext:
    """Prepared Codex SDK resume context."""

    thread_id: str
    sdk_module: ModuleType


class CodexRewakeBackend:
    """Resume Codex SDK continuation when explicitly enabled."""

    def __init__(
        self,
        registry: WaitRegistry,
        *,
        env: Mapping[str, str] | None = None,
        importer: ImportModule = import_module,
    ) -> None:
        self._registry = registry
        self._env = os.environ if env is None else env
        self._importer = importer

    def enabled(self) -> bool:
        """Return whether SDK rewake is enabled."""

        return codex_rewake_enabled(self._env)

    def resume_if_available(self, record: WaitRecord) -> CodexRewakeResult:
        """Resume Codex thread when SDK metadata is available."""

        resume_target = self._resume_context(record)
        if isinstance(resume_target, CodexRewakeResult):
            return resume_target
        prompt = continuation_prompt(record)
        try:
            self._resume_with_thread(
                resume_target.sdk_module,
                resume_target.thread_id,
                prompt,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return _manual_result(record, f"Codex SDK rewake failed: {exc}")
        self._registry.mark_resumed(record)
        return CodexRewakeResult(
            REWAKE_STATUS_RESUMED,
            "Codex SDK continuation started",
            prompt=prompt,
        )

    def _resume_context(self, record: WaitRecord) -> _RewakeContext | CodexRewakeResult:
        """Return prepared resume context or terminal non-resume result."""

        if not self.enabled():
            return CodexRewakeResult(REWAKE_STATUS_DISABLED, "Codex SDK rewake disabled")
        if not _codex_record_ready(record):
            return CodexRewakeResult(REWAKE_STATUS_SKIPPED, "wait not ready Codex")
        thread_id = codex_thread_id(self._env)
        if not thread_id:
            return _manual_result(record, "Codex thread id unavailable")
        sdk_module = self._sdk_module()
        if sdk_module is None:
            return _manual_result(record, "openai-codex SDK is unavailable")
        return _RewakeContext(thread_id=thread_id, sdk_module=sdk_module)

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

    def _sdk_module(self) -> ModuleType | None:
        try:
            return self._importer(OPENAI_CODEX_PACKAGE)
        except ImportError:
            return None


def codex_rewake_enabled(env: Mapping[str, str]) -> bool:
    """Return whether Codex rewake is enabled."""

    return env.get(CODEX_REWAKE_ENV) == "1"


def codex_thread_id(env: Mapping[str, str]) -> str:
    """Return Codex thread metadata from explicit or inherited environment."""

    return env.get(CODEX_THREAD_ID_OVERRIDE_ENV) or env.get(CODEX_THREAD_ID_ENV, "")


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
