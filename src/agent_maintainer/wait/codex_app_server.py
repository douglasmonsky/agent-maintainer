"""Codex app-server JSON-RPC continuation client."""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from subprocess import PIPE, Popen, TimeoutExpired  # nosec B404
from typing import Final, TextIO

APP_SERVER_COMPLETED_METHODS: Final = frozenset(("turn/completed", "turn.completed"))
APP_SERVER_TURN_START_REQUEST_ID: Final = 3
APP_SERVER_THREAD_READ_REQUEST_START_ID: Final = 1000
APP_SERVER_THREAD_READ_POLL_SECONDS: Final = 2.0
APP_SERVER_STDERR_LIMIT: Final = 2000
APP_SERVER_TERMINAL_TURN_STATUSES: Final = frozenset(
    ("completed", "failed", "interrupted"),
)

PopenFactory = Callable[..., Popen[str]]
LineQueue = queue.Queue[str | None]


@dataclass(frozen=True)
class _JsonRpcResponse:
    """Observed app-server JSON-RPC response."""

    request_id: int
    result: Mapping[str, object] | None = None
    error: str = ""


@dataclass
class _AppServerWaitState:
    """Mutable app-server turn wait state."""

    turn_accepted: bool = False
    turn_id: str = ""
    next_thread_read_request_id: int = APP_SERVER_THREAD_READ_REQUEST_START_ID
    last_thread_read_requested_at: float = 0
    completed: bool = False


class CodexAppServerClient:
    """Minimal Codex app-server JSON-RPC rewake client."""

    def __init__(
        self,
        *,
        codex_bin: str,
        timeout_seconds: float,
        popen_factory: PopenFactory = Popen,
        thread_read_poll_seconds: float = APP_SERVER_THREAD_READ_POLL_SECONDS,
        return_after_turn_acceptance: bool = False,
    ) -> None:
        self._codex_bin = codex_bin
        self._timeout_seconds = timeout_seconds
        self._popen_factory = popen_factory
        self._thread_read_poll_seconds = thread_read_poll_seconds
        self._return_after_turn_acceptance = return_after_turn_acceptance

    def resume_thread(self, thread_id: str, prompt: str) -> None:
        """Resume thread, start one turn, and wait for completion."""

        process = self._start_process()
        try:
            self._resume_process(process, thread_id, prompt)
        except (OSError, RuntimeError, TimeoutError):
            _stop_process(process)
            raise
        if self._return_after_turn_acceptance:
            _detach_process(process)
        else:
            _stop_process(process)

    def command(self) -> tuple[str, str, str, str]:
        """Return Codex app-server command."""

        return (self._codex_bin, "app-server", "--listen", "stdio://")

    def _start_process(self) -> Popen[str]:
        return self._popen_factory(
            list(self.command()),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )

    def _send_start_turn(
        self,
        process: Popen[str],
        thread_id: str,
        prompt: str,
    ) -> None:
        if process.stdin is None:
            raise RuntimeError("Codex app-server stdin unavailable")
        for message in _app_server_messages(thread_id, prompt):
            process.stdin.write(f"{json.dumps(message, separators=(',', ':'))}\n")
        process.stdin.flush()

    def _resume_process(
        self,
        process: Popen[str],
        thread_id: str,
        prompt: str,
    ) -> None:
        self._send_start_turn(process, thread_id, prompt)
        self._wait_for_completion(process, thread_id)

    def _wait_for_completion(
        self,
        process: Popen[str],
        thread_id: str,
    ) -> None:
        if process.stdout is None:
            raise RuntimeError("Codex app-server stdout unavailable")
        lines: LineQueue = queue.Queue()
        stdout_thread = threading.Thread(
            target=_read_app_server_stdout,
            args=(process.stdout, lines),
            daemon=True,
        )
        stdout_thread.start()
        deadline = time.monotonic() + self._timeout_seconds
        state = _AppServerWaitState()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Codex app-server rewake timed out")
            _maybe_request_thread_read(
                process,
                thread_id,
                state,
                poll_seconds=self._thread_read_poll_seconds,
            )
            line = _get_app_server_line(lines, timeout=min(remaining, 1.0))
            if line is not None:
                if _consume_app_server_wait_line(
                    line,
                    state,
                    return_after_turn_acceptance=self._return_after_turn_acceptance,
                ):
                    return
                continue
            if process.poll() is not None:
                stderr = _bounded_stderr(process)
                raise RuntimeError(f"Codex app-server exited early{stderr}")


def _app_server_messages(thread_id: str, prompt: str) -> tuple[dict[str, object], ...]:
    return (
        {
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "agent_maintainer",
                    "title": "Agent Maintainer",
                    "version": "0.0.0",
                },
            },
        },
        {"method": "initialized", "params": {}},
        {"id": 2, "method": "thread/resume", "params": {"threadId": thread_id}},
        {
            "id": APP_SERVER_TURN_START_REQUEST_ID,
            "method": "turn/start",
            "params": {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt}],
            },
        },
    )


def _read_app_server_stdout(
    stdout: TextIO,
    lines: LineQueue,
) -> None:
    for line in stdout:
        lines.put(str(line))
    lines.put(None)


def _get_app_server_line(lines: LineQueue, *, timeout: float) -> str | None:
    try:
        return lines.get(timeout=timeout)
    except queue.Empty:
        return None


def _consume_app_server_wait_line(
    line: str,
    state: _AppServerWaitState,
    *,
    return_after_turn_acceptance: bool,
) -> bool:
    _consume_app_server_line(line, state)
    return _app_server_wait_satisfied(
        state,
        return_after_turn_acceptance=return_after_turn_acceptance,
    )


def _app_server_wait_satisfied(
    state: _AppServerWaitState,
    *,
    return_after_turn_acceptance: bool,
) -> bool:
    return state.completed or (state.turn_accepted and return_after_turn_acceptance)


def _consume_app_server_line(line: str, state: _AppServerWaitState) -> None:
    response = _parse_app_server_line(line)
    if response is not None:
        if response.error:
            raise RuntimeError(response.error)
        _consume_app_server_response(response, state)
        return
    if not _app_server_turn_completed(line):
        return
    if not state.turn_accepted:
        raise RuntimeError("Codex app-server completed unaccepted turn")
    state.completed = True


def _consume_app_server_response(
    response: _JsonRpcResponse,
    state: _AppServerWaitState,
) -> None:
    if response.request_id == APP_SERVER_TURN_START_REQUEST_ID:
        state.turn_accepted = True
        _update_turn_state(response.result, state)
        return
    if response.request_id >= APP_SERVER_THREAD_READ_REQUEST_START_ID:
        _update_turn_state(response.result, state)


def _parse_app_server_line(line: str) -> _JsonRpcResponse | None:
    payload = _json_object(line)
    request_id = payload.get("id")
    if not isinstance(request_id, int):
        return None
    error = payload.get("error")
    if isinstance(error, Mapping):
        message = error.get("message")
        return _JsonRpcResponse(
            request_id,
            error=str(message or "Codex app-server error"),
        )
    result = payload.get("result")
    return _JsonRpcResponse(
        request_id,
        result=result if isinstance(result, Mapping) else None,
    )


def _update_turn_state(
    result: Mapping[str, object] | None,
    state: _AppServerWaitState,
) -> None:
    if result is None:
        return
    turn = _turn_from_result(result, state.turn_id)
    if turn is None:
        return
    turn_id = turn.get("id")
    if isinstance(turn_id, str) and turn_id:
        state.turn_id = turn_id
    status = turn.get("status")
    if not isinstance(status, str):
        return
    if status == "completed":
        state.completed = True
    elif status in APP_SERVER_TERMINAL_TURN_STATUSES:
        raise RuntimeError(f"Codex app-server turn ended with status {status}")


def _turn_from_result(
    result: Mapping[str, object],
    turn_id: str,
) -> Mapping[str, object] | None:
    turn = result.get("turn")
    if isinstance(turn, Mapping):
        return turn
    thread = result.get("thread")
    if not isinstance(thread, Mapping):
        return None
    turns = thread.get("turns")
    if not isinstance(turns, list):
        return None
    for item in reversed(turns):
        if not isinstance(item, Mapping):
            continue
        if not turn_id or item.get("id") == turn_id:
            return item
    return None


def _maybe_request_thread_read(
    process: Popen[str],
    thread_id: str,
    state: _AppServerWaitState,
    *,
    poll_seconds: float,
) -> None:
    if not state.turn_accepted or not state.turn_id:
        return
    current = time.monotonic()
    if current - state.last_thread_read_requested_at < poll_seconds:
        return
    if process.stdin is None:
        raise RuntimeError("Codex app-server stdin unavailable")
    request_id = state.next_thread_read_request_id
    state.next_thread_read_request_id += 1
    state.last_thread_read_requested_at = current
    message = {
        "id": request_id,
        "method": "thread/read",
        "params": {"threadId": thread_id, "includeTurns": True},
    }
    process.stdin.write(f"{json.dumps(message, separators=(',', ':'))}\n")
    process.stdin.flush()


def _app_server_turn_completed(line: str) -> bool:
    payload = _json_object(line)
    method = payload.get("method")
    event_type = payload.get("type")
    return method in APP_SERVER_COMPLETED_METHODS or event_type in APP_SERVER_COMPLETED_METHODS


def _json_object(line: str) -> dict[str, object]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _bounded_stderr(process: Popen[str]) -> str:
    if process.stderr is None:
        return ""
    stderr = process.stderr.read(APP_SERVER_STDERR_LIMIT).strip()
    if not stderr:
        return ""
    return f": {stderr}"


def _stop_process(process: Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _detach_process(process: Popen[str]) -> None:
    if process.stdin is not None:
        process.stdin.close()
    threading.Thread(
        target=_drain_detached_process,
        args=(process,),
        daemon=True,
    ).start()


def _drain_detached_process(process: Popen[str]) -> None:
    if process.stderr is not None:
        process.stderr.read()
    process.wait(timeout=None)
