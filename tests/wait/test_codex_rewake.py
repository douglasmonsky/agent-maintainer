"""Tests optional Codex rewake backend."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import ClassVar

import pytest

from agent_maintainer.wait import codex_rewake as codex_rewake_module
from agent_maintainer.wait.codex_rewake import (
    CODEX_BIN_ENV,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    REWAKE_STATUS_DISABLED,
    REWAKE_STATUS_MANUAL,
    CodexRewakeBackend,
    CodexRewakeResult,
    codex_rewake_resumed,
    continuation_prompt,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import (
    WAIT_STATUS_READY,
    WAIT_STATUS_RESUMED,
    RegisterGitHubPrWait,
    WaitRecord,
    WaitRegistry,
)

PR_NUMBER = "291"
THREAD_ID = "thread-1"
CodexCall = tuple[str, str]
CodexCalls = list[CodexCall]


def test_backend_skips_without_feature_flag(tmp_path: Path) -> None:
    """Codex rewake does nothing unless explicitly enabled."""

    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={CODEX_THREAD_ID_ENV: THREAD_ID},
        importer=fake_importer,
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_DISABLED
    assert registry.read(record.wait_id).status == WAIT_STATUS_READY
    assert not FakeCodex.calls


def test_backend_stays_manual_without_thread(tmp_path: Path) -> None:
    """Enabled rewake leaves manual resume ready without thread metadata."""

    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={CODEX_REWAKE_ENV: "1"},
        importer=fake_importer,
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert "wait resume" in result.detail
    assert registry.read(record.wait_id).status == WAIT_STATUS_READY


def test_backend_stays_manual_without_backend(tmp_path: Path) -> None:
    """Enabled rewake leaves manual resume ready without SDK import."""

    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_BIN_ENV: "/missing/codex",
        },
        importer=missing_importer,
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert "Codex app-server rewake failed" in result.detail
    assert registry.read(record.wait_id).status == WAIT_STATUS_READY


def test_backend_runs_app_server_and_marks_resumed(tmp_path: Path) -> None:
    """Enabled rewake uses app-server before SDK."""

    FakeCodex.calls = []
    app_server = FakeAppServerClient()
    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_BIN_ENV: "codex-test",
        },
        importer=fake_importer,
        app_server_client=app_server,
    ).resume_if_available(record)

    assert_backend_success(result, registry, record)
    assert app_server.calls == [(THREAD_ID, continuation_prompt(record))]
    assert not FakeCodex.calls
    assert_private_data_not_persisted(tmp_path, record)


def test_backend_app_server_returns_after_turn_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daemon rewake marks resumed after Codex accepts continuation turn."""

    clients: list[CapturingAppServerClient] = []

    def client_factory(**kwargs: object) -> CapturingAppServerClient:
        client = CapturingAppServerClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(codex_rewake_module, "CodexAppServerClient", client_factory)
    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_BIN_ENV: "codex-test",
        },
        importer=fake_importer,
    ).resume_if_available(record)

    assert_backend_success(result, registry, record)
    assert len(clients) == 1
    assert clients[0].return_after_turn_acceptance is True
    assert clients[0].calls == [(THREAD_ID, continuation_prompt(record))]


def test_backend_runs_sdk_and_marks_resumed(tmp_path: Path) -> None:
    """Enabled rewake sends continuation prompt and consumes wait record."""

    FakeCodex.calls = []
    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_BIN_ENV: "/missing/codex",
        },
        importer=fake_importer,
    ).resume_if_available(record)

    assert_backend_success(result, registry, record)
    assert_fake_calls(record)
    assert_private_data_not_persisted(tmp_path, record)


def completed_wait(registry: WaitRegistry, root: Path) -> WaitRecord:
    """Register and complete one successful Codex PR wait."""

    record = registry.register_github_pr(
        RegisterGitHubPrWait(root=root, pr_number=PR_NUMBER, platform="codex"),
    )
    return registry.complete_github_pr(
        record,
        GitHubPrWaitResult(
            pr_number=PR_NUMBER,
            state=GitHubPrChecksState(
                pr_number=PR_NUMBER,
                checks=(GitHubPrCheck(name="verify", state="success"),),
            ),
        ),
    )


def wait_record_path(root: Path, record: WaitRecord) -> Path:
    """Return durable wait record path."""

    return root / ".verify-logs" / "waits" / f"{record.wait_id}.json"


def assert_backend_success(
    result: CodexRewakeResult,
    registry: WaitRegistry,
    record: WaitRecord,
) -> None:
    """Assert the backend consumed a terminal wait record."""

    assert codex_rewake_resumed(result)
    assert result.prompt == continuation_prompt(record)
    assert registry.read(record.wait_id).status == WAIT_STATUS_RESUMED


def assert_fake_calls(record: WaitRecord) -> None:
    """Assert fake SDK saw the expected thread and prompt."""

    assert FakeCodex.calls == [
        ("thread", THREAD_ID),
        ("prompt", continuation_prompt(record)),
    ]


def assert_private_data_not_persisted(root: Path, record: WaitRecord) -> None:
    """Assert transient Codex rewake data stayed out of durable records."""

    raw_record = wait_record_path(root, record).read_text(encoding="utf-8")
    assert THREAD_ID not in raw_record
    assert continuation_prompt(record) not in raw_record


def fake_importer(_name: str) -> ModuleType:
    """Return a fake openai-codex SDK module."""

    module = FakeOpenaiCodex("openai_codex")
    if module.sdk_name() != _name:
        raise ImportError(_name)
    return module


def missing_importer(_name: str) -> ModuleType:
    """Raise the optional SDK import error."""

    raise ImportError("missing")


class FakeAppServerClient:
    """Fake app-server client recording resume prompt calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def resume_thread(self, thread_id: str, prompt: str) -> None:
        """Record app-server resume request."""

        self.calls.append((thread_id, prompt))


class CapturingAppServerClient:
    """Fake constructed app-server client recording constructor options."""

    def __init__(self, **kwargs: object) -> None:
        self.return_after_turn_acceptance = kwargs.get("return_after_turn_acceptance")
        self.calls: list[tuple[str, str]] = []

    def resume_thread(self, thread_id: str, prompt: str) -> None:
        """Record app-server resume request."""

        self.calls.append((thread_id, prompt))


class FakeCodex:
    """Fake Codex SDK client recording resume and prompt calls."""

    calls: ClassVar[CodexCalls] = []

    def __enter__(self) -> FakeCodex:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def __getattr__(self, name: str) -> object:
        if name == "thread_resume":
            return self._resume
        raise AttributeError(name)

    def _resume(self, thread_id: str) -> FakeThread:
        self.calls.append(("thread", thread_id))
        thread = FakeThread(self.calls)
        thread.call_count()
        return thread


class FakeOpenaiCodex(ModuleType):
    """Fake openai-codex module exposing the Codex client class."""

    def __getattr__(self, name: str) -> object:
        if name == "Codex":
            return FakeCodex
        raise AttributeError(name)

    def sdk_name(self) -> str:
        """Return fake SDK package name."""

        return self.__name__


class FakeThread:
    """Fake resumed Codex thread."""

    def __init__(self, calls: CodexCalls) -> None:
        self._calls = calls

    def run(self, prompt: str) -> None:
        self._calls.append(("prompt", prompt))

    def call_count(self) -> int:
        """Return count of fake SDK calls."""

        return len(self._calls)
