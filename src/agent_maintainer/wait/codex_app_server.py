"""Codex app-server JSON-RPC continuation client."""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from subprocess import PIPE, Popen, TimeoutExpired  # nosec B404
from typing import Final, TextIO

from agent_maintainer.wait import codex_app_server_protocol as protocol

APP_SERVER_THREAD_READ_POLL_SECONDS: Final = 2.0
APP_SERVER_STDERR_LIMIT: Final = 2000


@dataclass
class _AppServerWaitState:
    """Mutable app-server turn wait state."""

    turn_accepted: bool = False
    turn_id: str = ""
    next_thread_read_request_id: int = protocol.APP_SERVER_THREAD_READ_REQUEST_START_ID
    last_thread_read_requested_at: float = 0
    completed: bool = False


class CodexAppServerClient:
    """Minimal Codex app-server JSON-RPC rewake client."""

    def __init__(
        self,
        *,
        codex_bin: str,
        timeout_seconds: float,
        popen_factory: Callable[..., Popen[str]] = Popen,
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

    def probe_thread(self, thread_id: str) -> None:
        """Read one thread through app-server without starting a turn."""

        with ExitStack() as cleanup:
            process = self._start_process()
            cleanup.callback(_stop_process, process)
            _probe_process(process, thread_id, self._timeout_seconds)

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

    def _resume_process(
        self,
        process: Popen[str],
        thread_id: str,
        prompt: str,
    ) -> None:
        _send_messages(process, protocol.app_server_messages(thread_id, prompt))
        self._wait_for_completion(process, thread_id)

    def _wait_for_completion(
        self,
        process: Popen[str],
        thread_id: str,
    ) -> None:
        lines = _app_server_line_queue(process)
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


def _send_messages(
    process: Popen[str],
    messages: tuple[dict[str, object], ...],
) -> None:
    if process.stdin is None:
        raise RuntimeError("Codex app-server stdin unavailable")
    for message in messages:
        process.stdin.write(f"{json.dumps(message, separators=(',', ':'))}\n")
    process.stdin.flush()


def _probe_process(
    process: Popen[str],
    thread_id: str,
    timeout_seconds: float,
) -> None:
    _send_messages(process, protocol.app_server_probe_messages(thread_id))
    _wait_for_response(
        process,
        protocol.APP_SERVER_THREAD_READ_PROBE_REQUEST_ID,
        timeout_seconds,
    )


def _wait_for_response(
    process: Popen[str],
    request_id: int,
    timeout_seconds: float,
) -> None:
    lines = _app_server_line_queue(process)
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Codex app-server probe timed out")
        line = _get_app_server_line(lines, timeout=min(remaining, 1.0))
        if line is not None and _requested_response_received(line, request_id):
            return
        if process.poll() is not None:
            stderr = _bounded_stderr(process)
            raise RuntimeError(f"Codex app-server exited early{stderr}")


def _requested_response_received(line: str, request_id: int) -> bool:
    response = protocol.parse_app_server_line(line)
    if response is None:
        return False
    if response.error:
        raise RuntimeError(response.error)
    return response.request_id == request_id


def _app_server_line_queue(process: Popen[str]) -> queue.Queue[str | None]:
    if process.stdout is None:
        raise RuntimeError("Codex app-server stdout unavailable")
    lines: queue.Queue[str | None] = queue.Queue()
    stdout_thread = threading.Thread(
        target=_read_app_server_stdout,
        args=(process.stdout, lines),
        daemon=True,
    )
    stdout_thread.start()
    return lines


def _read_app_server_stdout(
    stdout: TextIO,
    lines: queue.Queue[str | None],
) -> None:
    for line in stdout:
        lines.put(str(line))
    lines.put(None)


def _get_app_server_line(
    lines: queue.Queue[str | None],
    *,
    timeout: float,
) -> str | None:
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
    response = protocol.parse_app_server_line(line)
    if response is not None:
        if response.error:
            raise RuntimeError(response.error)
        _consume_app_server_response(response, state)
        return
    if not protocol.app_server_turn_completed(line):
        return
    if not state.turn_accepted:
        raise RuntimeError("Codex app-server completed unaccepted turn")
    state.completed = True


def _consume_app_server_response(
    response: protocol.JsonRpcResponse,
    state: _AppServerWaitState,
) -> None:
    if response.request_id == protocol.APP_SERVER_TURN_START_REQUEST_ID:
        state.turn_accepted = True
        _update_turn_state(response.result, state)
        return
    if response.request_id >= protocol.APP_SERVER_THREAD_READ_REQUEST_START_ID:
        _update_turn_state(response.result, state)


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
    elif status in protocol.APP_SERVER_TERMINAL_TURN_STATUSES:
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
