"""Tests gated, redacted Codex app-server smoke behavior."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agent_maintainer.wait import cli, codex_smoke
from agent_waits.capabilities import CODEX_BIN_ENV, CODEX_THREAD_ID_ENV

THREAD_ID = "thread-private-123"
CODEX_BIN = "/private/tools/codex"
GATE_REFUSAL_EXIT_CODE = 2
CUSTOM_TIMEOUT_SECONDS = 9.0


def test_read_only_smoke_probes_thread_without_leaking_context() -> None:
    """Default smoke performs only a redacted thread/read probe."""

    client = FakeSmokeClient()
    result = codex_smoke.run_codex_smoke(
        env={CODEX_THREAD_ID_ENV: THREAD_ID, CODEX_BIN_ENV: CODEX_BIN},
        start_turn=False,
        timeout_seconds=7,
        client_factory=lambda **kwargs: client.capture_options(kwargs),
    )

    assert result.exit_code == 0
    assert result.mode == codex_smoke.SMOKE_MODE_READ_ONLY
    assert client.probed == [THREAD_ID]
    assert client.resumed == []
    assert client.options["codex_bin"] == CODEX_BIN
    rendered = codex_smoke.render_codex_smoke_json(result)
    assert THREAD_ID not in rendered
    assert CODEX_BIN not in rendered


def test_turn_smoke_refuses_before_client_creation_without_explicit_gate() -> None:
    """A token-spending smoke cannot spawn app-server without explicit opt-in."""

    result = codex_smoke.run_codex_smoke(
        env={CODEX_THREAD_ID_ENV: THREAD_ID, CODEX_BIN_ENV: CODEX_BIN},
        start_turn=True,
        client_factory=unexpected_client_factory,
    )

    assert result.exit_code == GATE_REFUSAL_EXIT_CODE
    assert codex_smoke.CODEX_SMOKE_TURN_ENV in result.detail


def test_turn_smoke_uses_fixed_prompt_after_explicit_gate() -> None:
    """Opted-in turn smoke accepts no caller-controlled prompt text."""

    client = FakeSmokeClient()
    result = codex_smoke.run_codex_smoke(
        env={
            CODEX_THREAD_ID_ENV: THREAD_ID,
            CODEX_BIN_ENV: CODEX_BIN,
            codex_smoke.CODEX_SMOKE_TURN_ENV: "1",
        },
        start_turn=True,
        client_factory=lambda **kwargs: client.capture_options(kwargs),
    )

    assert result.exit_code == 0
    assert result.mode == codex_smoke.SMOKE_MODE_TURN
    assert client.resumed == [(THREAD_ID, codex_smoke.CODEX_SMOKE_PROMPT)]
    rendered = codex_smoke.render_codex_smoke_text(result)
    assert THREAD_ID not in rendered
    assert codex_smoke.CODEX_SMOKE_PROMPT not in rendered


def test_smoke_redacts_backend_exception_details() -> None:
    """App-server exceptions cannot leak response or environment content."""

    result = codex_smoke.run_codex_smoke(
        env={CODEX_THREAD_ID_ENV: THREAD_ID, CODEX_BIN_ENV: CODEX_BIN},
        start_turn=False,
        client_factory=lambda **_kwargs: FailingSmokeClient(),
    )

    assert result.exit_code == 1
    assert "RuntimeError" in result.detail
    assert "private-api-key" not in result.detail


def test_codex_smoke_cli_renders_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Wait CLI exposes the smoke harness without adding durable state."""

    expected = codex_smoke.CodexSmokeResult(
        status="PASS",
        mode=codex_smoke.SMOKE_MODE_READ_ONLY,
        detail="Read-only Codex app-server probe passed.",
    )
    monkeypatch.setattr(codex_smoke, "run_codex_smoke", lambda **_kwargs: expected)

    status = cli.main(["codex-smoke", "--format", "json", "--timeout-seconds", "9"])

    assert status == 0
    assert json.loads(capsys.readouterr().out) == expected.as_dict()


def test_codex_smoke_parser_accepts_explicit_turn_gate_flag() -> None:
    args = cli.parse_args(["codex-smoke", "--start-turn", "--timeout-seconds", "9"])

    assert args.command == "codex-smoke"
    assert args.start_turn is True
    assert args.timeout_seconds == CUSTOM_TIMEOUT_SECONDS


class FakeSmokeClient:
    """Capture smoke calls without launching Codex."""

    def __init__(self) -> None:
        self.probed: list[str] = []
        self.resumed: list[tuple[str, str]] = []
        self.options: dict[str, Any] = {}

    def capture_options(self, options: dict[str, Any]) -> FakeSmokeClient:
        self.options = options
        return self

    def probe_thread(self, thread_id: str) -> None:
        self.probed.append(thread_id)

    def resume_thread(self, thread_id: str, prompt: str) -> None:
        self.resumed.append((thread_id, prompt))


class FailingSmokeClient:
    def probe_thread(self, _thread_id: str) -> None:
        raise RuntimeError("private-api-key")


def unexpected_client_factory(**_kwargs: object) -> FakeSmokeClient:
    raise AssertionError("client must not be created before the spend gate")
