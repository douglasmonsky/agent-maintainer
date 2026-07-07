"""Optional Codex SDK rewake backend for terminal wait records."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Any, Final, cast

from agent_maintainer.wait.models import WaitRepairCapsule, render_wait_capsule
from agent_maintainer.wait.registry import WaitRecord, WaitRegistry

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


class CodexRewakeBackend:
    """Resume a Codex SDK thread when terminal wait state is ready."""

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
        """Return whether this backend is configured to attempt rewake."""

        return codex_rewake_enabled(self._env)

    def resume_if_available(self, record: WaitRecord) -> CodexRewakeResult:
        """Attempt Codex SDK rewake or leave the record ready for manual resume."""

        if not _codex_record_ready(record):
            return CodexRewakeResult(REWAKE_STATUS_SKIPPED, "wait is not a ready Codex record")
        if not self.enabled():
            return CodexRewakeResult(REWAKE_STATUS_DISABLED, "Codex rewake is disabled")

        thread_id = codex_thread_id(self._env)
        if not thread_id:
            return _manual_result(record, "Codex thread metadata is unavailable")
        return self._resume_with_thread(record, thread_id)

    def _resume_with_thread(self, record: WaitRecord, thread_id: str) -> CodexRewakeResult:
        sdk_module = self._sdk_module()
        if sdk_module is None:
            return _manual_result(record, "openai-codex SDK is unavailable")

        prompt = continuation_prompt(record)
        try:
            _run_sdk_rewake(sdk_module, thread_id, prompt)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return _manual_result(record, f"Codex SDK rewake failed: {exc}")

        self._registry.mark_resumed(record)
        return CodexRewakeResult(
            REWAKE_STATUS_RESUMED,
            "Codex SDK continuation started",
            prompt=prompt,
        )

    def _sdk_module(self) -> ModuleType | None:
        try:
            return self._importer(OPENAI_CODEX_PACKAGE)
        except ImportError:
            return None


def codex_rewake_enabled(env: Mapping[str, str]) -> bool:
    """Return whether automatic Codex rewake is enabled."""

    return env.get(CODEX_REWAKE_ENV) == "1"


def codex_thread_id(env: Mapping[str, str]) -> str:
    """Return Codex thread metadata from explicit or inherited environment."""

    return env.get(CODEX_THREAD_ID_OVERRIDE_ENV) or env.get(CODEX_THREAD_ID_ENV, "")


def continuation_prompt(record: WaitRecord) -> str:
    """Return the Codex continuation prompt for one terminal PR wait."""

    return (
        f"PR checks reached {record.terminal_result} for PR #{record.pr_number}. "
        "Review the PR diff, inspect failures if any, merge only if satisfactory, "
        "then continue the prior roadmap task."
    )


def codex_rewake_resumed(result: CodexRewakeResult) -> bool:
    """Return whether a Codex continuation was started."""

    return result.status == REWAKE_STATUS_RESUMED


def render_codex_rewake_text(record: WaitRecord, result: CodexRewakeResult) -> str:
    """Render compact output for a successful Codex rewake."""

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
        f"{detail}; run `{record.resume_instruction}`",
    )


def _run_sdk_rewake(sdk_module: ModuleType, thread_id: str, prompt: str) -> None:
    codex_factory = getattr(sdk_module, "Codex", None)
    if not callable(codex_factory):
        raise RuntimeError("openai_codex.Codex is unavailable")

    codex_context = cast("Any", codex_factory())
    with codex_context as codex:
        thread = _resume_thread(codex, thread_id)
        run = getattr(thread, "run", None)
        if not callable(run):
            raise RuntimeError("Codex SDK thread.run is unavailable")
        run(prompt)


def _resume_thread(codex: Any, thread_id: str) -> Any:
    for method_name in SDK_RESUME_METHODS:
        method = getattr(codex, method_name, None)
        if callable(method):
            return method(thread_id)
    raise RuntimeError("Codex SDK thread resume method is unavailable")
