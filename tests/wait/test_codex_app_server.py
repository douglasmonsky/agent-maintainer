"""Tests Codex app-server JSON-RPC client."""

from __future__ import annotations

import json
import queue
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any, cast

import pytest

from agent_maintainer.wait.codex_app_server import (
    CodexAppServerClient,
    _AppServerWaitState,
    _bounded_stderr,
    _consume_app_server_line,
    _get_app_server_line,
    _maybe_request_thread_read,
    _stop_process,
    _turn_from_result,
    _update_turn_state,
)
from agent_maintainer.wait.codex_app_server_protocol import (
    _json_object,
    app_server_turn_completed,
    parse_app_server_line,
)

THREAD_ID = "thread-1"


def test_app_server_client_runs_json_rpc_turn(tmp_path: Path) -> None:
    """App-server client sends resume/start messages and waits for completion."""

    script = tmp_path / "fake_app_server.py"
    log_path = tmp_path / "messages.jsonl"
    script.write_text(
        """
import json
import pathlib
import sys

log_path = pathlib.Path(sys.argv[1])
with log_path.open("w", encoding="utf-8") as log:
    for line in sys.stdin:
        message = json.loads(line)
        log.write(json.dumps(message, sort_keys=True) + "\\n")
        log.flush()
        request_id = message.get("id")
        if request_id is not None:
            print(json.dumps({"id": request_id, "result": {}}), flush=True)
        if message.get("method") == "turn/start":
            print(json.dumps({"method": "turn/completed", "params": {}}), flush=True)
            break
""",
        encoding="utf-8",
    )

    def popen_factory(
        _command: list[str],
        **kwargs: Any,
    ) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, str(script), str(log_path)],
            **kwargs,
        )

    client = CodexAppServerClient(
        codex_bin="codex-test",
        timeout_seconds=5,
        popen_factory=popen_factory,
        thread_read_poll_seconds=0.01,
    )

    client.resume_thread(THREAD_ID, "continue now")

    messages = [
        message["method"]
        for message in (
            json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert messages == ["initialize", "initialized", "thread/resume", "turn/start"]


def test_app_server_client_can_return_after_turn_acceptance(tmp_path: Path) -> None:
    """App-server client can stop after turn/start is accepted."""

    script = tmp_path / "fake_app_server_accept.py"
    log_path = tmp_path / "accept-messages.jsonl"
    script.write_text(
        """
import json
import pathlib
import sys

log_path = pathlib.Path(sys.argv[1])
with log_path.open("w", encoding="utf-8") as log:
    for line in sys.stdin:
        message = json.loads(line)
        log.write(json.dumps(message, sort_keys=True) + "\\n")
        log.flush()
        request_id = message.get("id")
        method = message.get("method")
        if method == "turn/start":
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "result": {"turn": {"id": "turn-1", "status": "inProgress"}},
                    }
                ),
                flush=True,
            )
        elif request_id is not None:
            print(json.dumps({"id": request_id, "result": {}}), flush=True)
""",
        encoding="utf-8",
    )

    def popen_factory(
        _command: list[str],
        **kwargs: Any,
    ) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, str(script), str(log_path)],
            **kwargs,
        )

    client = CodexAppServerClient(
        codex_bin="codex-test",
        timeout_seconds=5,
        popen_factory=popen_factory,
        thread_read_poll_seconds=0.01,
        return_after_turn_acceptance=True,
    )

    client.resume_thread(THREAD_ID, "continue now")

    methods = [
        message["method"]
        for message in (
            json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert methods == ["initialize", "initialized", "thread/resume", "turn/start"]


def test_app_server_client_polls_thread_read_when_completion_not_streamed(
    tmp_path: Path,
) -> None:
    """App-server client falls back to thread/read turn status polling."""

    script = tmp_path / "fake_app_server_poll.py"
    log_path = tmp_path / "poll-messages.jsonl"
    script.write_text(
        """
import json
import pathlib
import sys

log_path = pathlib.Path(sys.argv[1])
with log_path.open("w", encoding="utf-8") as log:
    for line in sys.stdin:
        message = json.loads(line)
        log.write(json.dumps(message, sort_keys=True) + "\\n")
        log.flush()
        request_id = message.get("id")
        method = message.get("method")
        if method == "turn/start":
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "result": {"turn": {"id": "turn-1", "status": "inProgress"}},
                    }
                ),
                flush=True,
            )
            continue
        if method == "thread/read":
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "result": {
                            "thread": {
                                "turns": [
                                    {"id": "turn-1", "status": "completed"}
                                ]
                            }
                        },
                    }
                ),
                flush=True,
            )
            break
        if request_id is not None:
            print(json.dumps({"id": request_id, "result": {}}), flush=True)
""",
        encoding="utf-8",
    )

    def popen_factory(
        _command: list[str],
        **kwargs: Any,
    ) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, str(script), str(log_path)],
            **kwargs,
        )

    client = CodexAppServerClient(
        codex_bin="codex-test",
        timeout_seconds=5,
        popen_factory=popen_factory,
        thread_read_poll_seconds=0.01,
    )

    client.resume_thread(THREAD_ID, "continue now")

    methods = [
        message["method"]
        for message in (
            json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert methods == [
        "initialize",
        "initialized",
        "thread/resume",
        "turn/start",
        "thread/read",
    ]


def test_app_server_completion_accepts_known_event_spellings() -> None:
    """Completion parsing accepts canonical and compatibility event names."""

    assert app_server_turn_completed(json.dumps({"method": "turn/completed"}))
    assert app_server_turn_completed(json.dumps({"method": "turn.completed"}))
    assert app_server_turn_completed(json.dumps({"type": "turn/completed"}))
    assert not app_server_turn_completed(json.dumps({"method": "turn/started"}))


def test_app_server_completion_requires_accepted_turn() -> None:
    """Completion events before turn acceptance fail closed."""

    with pytest.raises(RuntimeError, match="completed unaccepted turn"):
        _consume_app_server_line(
            json.dumps({"method": "turn/completed"}),
            _AppServerWaitState(),
        )


def test_app_server_line_queue_timeout_returns_none() -> None:
    """Timed queue reads return None while app-server is still quiet."""

    lines: queue.Queue[str | None] = queue.Queue()

    assert _get_app_server_line(lines, timeout=0.01) is None


def test_app_server_json_helpers_ignore_invalid_payloads() -> None:
    """App-server JSON parsing ignores non-object or malformed messages."""

    assert _json_object("not-json") == {}
    assert _json_object("[]") == {}
    assert parse_app_server_line(json.dumps({"id": "not-int"})) is None
    response = parse_app_server_line(
        json.dumps({"id": 9, "error": {"message": "boom"}}),
    )

    assert response is not None
    assert response.error == "boom"


def test_app_server_turn_state_handles_terminal_and_ignored_shapes() -> None:
    """Turn status extraction handles missing, completed, and failed states."""

    state = _AppServerWaitState()
    _update_turn_state(None, state)
    _update_turn_state({"thread": {"turns": "not-list"}}, state)
    _update_turn_state({"turn": {"id": "turn-1"}}, state)

    assert not state.completed
    assert _turn_from_result({"thread": {"turns": [object()]}}, "turn-1") is None

    _update_turn_state(
        {"thread": {"turns": [{"id": "turn-1", "status": "completed"}]}},
        state,
    )

    assert state.turn_id == "turn-1"
    assert state.completed

    with pytest.raises(RuntimeError, match="status failed"):
        _update_turn_state(
            {"turn": {"id": "turn-2", "status": "failed"}},
            _AppServerWaitState(),
        )


def test_app_server_thread_read_polling_writes_when_due() -> None:
    """Thread-read polling writes only when a turn is accepted and known."""

    process = FakeTextProcess()
    state = _AppServerWaitState()

    _maybe_request_thread_read(cast(Any, process), THREAD_ID, state, poll_seconds=0)
    assert process.stdin is not None
    assert process.stdin.getvalue() == ""

    state.turn_accepted = True
    state.turn_id = "turn-1"
    _maybe_request_thread_read(cast(Any, process), THREAD_ID, state, poll_seconds=0)

    assert process.stdin is not None
    assert '"method":"thread/read"' in process.stdin.getvalue()


def test_app_server_thread_read_polling_requires_stdin() -> None:
    """Thread-read polling fails clearly if app-server stdin is unavailable."""

    process = FakeTextProcess()
    process.stdin = None
    state = _AppServerWaitState(turn_accepted=True, turn_id="turn-1")

    with pytest.raises(RuntimeError, match="stdin unavailable"):
        _maybe_request_thread_read(cast(Any, process), THREAD_ID, state, poll_seconds=0)


def test_app_server_wait_handles_unavailable_stdout_and_exit() -> None:
    """App-server wait reports missing stdout and early process exits."""

    client = CodexAppServerClient(codex_bin="codex-test", timeout_seconds=0.01)

    with pytest.raises(RuntimeError, match="stdout unavailable"):
        process = FakeTextProcess()
        process.stdout = None
        client._wait_for_completion(cast(Any, process), THREAD_ID)

    with pytest.raises(RuntimeError, match="exited early: boom"):
        client._wait_for_completion(
            cast(
                Any,
                FakeTextProcess(stdout=StringIO(""), stderr=StringIO("boom"), poll_result=1),
            ),
            THREAD_ID,
        )


def test_app_server_wait_times_out_when_process_stays_quiet() -> None:
    """App-server wait times out when no line or process exit arrives."""

    client = CodexAppServerClient(codex_bin="codex-test", timeout_seconds=0.01)

    with pytest.raises(TimeoutError, match="rewake timed out"):
        client._wait_for_completion(
            cast(Any, FakeTextProcess(stdout=StringIO(""))),
            THREAD_ID,
        )


def test_app_server_process_helpers_cover_stderr_and_kill() -> None:
    """Process helpers bound stderr and kill stubborn app-server processes."""

    process = FakeTextProcess()
    process.stderr = None
    assert _bounded_stderr(cast(Any, process)) == ""
    assert _bounded_stderr(cast(Any, FakeTextProcess(stderr=StringIO("")))) == ""
    assert _bounded_stderr(cast(Any, FakeTextProcess(stderr=StringIO("boom")))) == ": boom"

    process = StubbornProcess()
    _stop_process(cast(Any, process))

    assert process.terminated
    assert process.killed


def test_probe_stops_process_when_interrupted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read-only probing always reaps its app-server child on interruption."""

    process = StubbornProcess()
    client = CodexAppServerClient(
        codex_bin="codex-test",
        timeout_seconds=1,
        popen_factory=lambda *_args, **_kwargs: cast(Any, process),
    )

    def interrupt_probe(*_args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "agent_maintainer.wait.codex_app_server._probe_process",
        interrupt_probe,
    )

    with pytest.raises(KeyboardInterrupt):
        client.probe_thread(THREAD_ID)

    assert process.terminated
    assert process.killed


class FakeTextProcess:
    """Small text-mode process double for app-server edge cases."""

    def __init__(
        self,
        *,
        stdin: StringIO | None = None,
        stdout: StringIO | None = None,
        stderr: StringIO | None = None,
        poll_result: int | None = None,
    ) -> None:
        self.stdin: StringIO | None = StringIO() if stdin is None else stdin
        self.stdout: StringIO | None = StringIO() if stdout is None else stdout
        self.stderr: StringIO | None = StringIO() if stderr is None else stderr
        self._poll_result = poll_result

    def poll(self) -> int | None:
        """Return configured process state."""

        return self._poll_result


class StubbornProcess(FakeTextProcess):
    """Process double that requires kill after terminate."""

    def __init__(self) -> None:
        super().__init__()
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        """Record terminate request."""

        self.terminated = True

    def wait(self, *, timeout: int) -> int:
        """Raise once after terminate, then report killed process exit."""

        if not self.killed:
            raise subprocess.TimeoutExpired("codex", timeout)
        return 0

    def kill(self) -> None:
        """Record kill request."""

        self.killed = True
