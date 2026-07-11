"""Tests optional Codex rewake backend."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.wait import codex_rewake as codex_rewake_module
from agent_maintainer.wait.codex_rewake import (
    CODEX_BIN_ENV,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    REWAKE_STATUS_DISABLED,
    REWAKE_STATUS_MANUAL,
    CodexRewakeBackend,
    continuation_prompt,
)
from agent_maintainer.wait.github_pr import (
    GitHubPrCheck,
    GitHubPrChecksState,
    GitHubPrWaitResult,
)
from agent_maintainer.wait.registry import (
    WAIT_STATUS_NOTIFY_FAILED,
    WAIT_STATUS_READY,
    RegisterGitHubPrWait,
    WaitRecord,
    WaitRegistry,
)

PR_NUMBER = "291"
THREAD_ID = "thread-1"


def test_backend_skips_without_feature_flag(tmp_path: Path) -> None:
    """Codex rewake does nothing unless explicitly enabled."""

    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={CODEX_THREAD_ID_ENV: THREAD_ID},
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_DISABLED
    assert registry.read(record.wait_id).status == WAIT_STATUS_READY


def test_backend_stays_manual_without_thread(tmp_path: Path) -> None:
    """Enabled rewake leaves manual resume ready without thread metadata."""

    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={CODEX_REWAKE_ENV: "1"},
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert "wait resume" in result.detail
    assert registry.read(record.wait_id).status == WAIT_STATUS_READY


def test_backend_stays_manual_without_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enabled rewake leaves manual resume ready without app-server."""

    monkeypatch.setattr(codex_rewake_module, "which", lambda _name: None)
    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: THREAD_ID,
        },
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert "Codex app-server unavailable" in result.detail
    assert registry.read(record.wait_id).status == WAIT_STATUS_READY


def test_backend_app_server_acceptance_stays_manual(tmp_path: Path) -> None:
    """Enabled app-server acceptance leaves manual resume ready."""
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
        app_server_client=app_server,
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert "visible thread wake is not confirmed" in result.detail
    persisted = registry.read(record.wait_id)
    assert persisted.status == WAIT_STATUS_NOTIFY_FAILED
    assert persisted.ready is True
    assert app_server.calls == [(THREAD_ID, continuation_prompt(record))]
    assert_private_data_not_persisted(tmp_path, record)


def test_backend_app_server_uses_acceptance_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Daemon rewake app-server mode returns after turn acceptance."""

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
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert registry.read(record.wait_id).status == WAIT_STATUS_NOTIFY_FAILED
    assert len(clients) == 1
    assert clients[0].return_after_turn_acceptance is True
    assert clients[0].calls == [(THREAD_ID, continuation_prompt(record))]


def test_backend_does_not_fallback_to_sdk(tmp_path: Path) -> None:
    """Enabled rewake leaves manual resume ready when app-server is unavailable."""
    registry = WaitRegistry(tmp_path)
    record = completed_wait(registry, tmp_path)

    result = CodexRewakeBackend(
        registry,
        env={
            CODEX_REWAKE_ENV: "1",
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_BIN_ENV: "/missing/codex",
        },
    ).resume_if_available(record)

    assert result.status == REWAKE_STATUS_MANUAL
    assert "Codex app-server rewake failed" in result.detail
    assert registry.read(record.wait_id).status == WAIT_STATUS_NOTIFY_FAILED
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


def assert_private_data_not_persisted(root: Path, record: WaitRecord) -> None:
    """Assert transient Codex rewake data stayed out of durable records."""

    raw_record = wait_record_path(root, record).read_text(encoding="utf-8")
    assert THREAD_ID not in raw_record
    assert continuation_prompt(record) not in raw_record


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
