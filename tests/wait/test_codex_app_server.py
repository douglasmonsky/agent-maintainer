"""Tests Codex app-server JSON-RPC client."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Protocol, cast

import pytest
from jsonschema import Draft202012Validator

from agent_maintainer.wait.codex_app_server import CodexAppServerClient
from agent_maintainer.wait.codex_app_server_protocol import (
    app_server_messages,
    app_server_probe_messages,
    app_server_turn_completed,
    parse_app_server_line,
)
from tests.support.paths import REPO_ROOT


class JsonValidator(Protocol):
    """Narrow interface used by dogfood schema assertions."""

    def validate(self, _instance: object) -> None:
        """Validate one JSON-compatible instance."""


THREAD_ID = "thread-1"


def test_app_server_schema_covers_consumed_and_emitted_messages() -> None:
    """Static JSON-RPC schema accepts every request and observed response shape."""
    schema = json.loads(
        (REPO_ROOT / "schemas/codex-app-server-wait.schema.json").read_text(encoding="utf-8")
    )
    validator = cast(JsonValidator, Draft202012Validator(schema))
    Draft202012Validator.check_schema(schema)
    messages: tuple[object, ...] = (
        *app_server_messages(THREAD_ID, "continue"),
        *app_server_probe_messages(THREAD_ID),
        {"id": 3, "result": {"turn": {"id": "turn-1", "status": "inProgress"}}},
        {"id": 3, "error": {"message": "request failed"}},
        {"method": "turn/completed", "params": {}},
        {"type": "turn/completed"},
    )

    for message in messages:
        validator.validate(message)


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
        **_kwargs: object,
    ) -> subprocess.Popen[str]:
        return _spawn_script(script, log_path)

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
        **_kwargs: object,
    ) -> subprocess.Popen[str]:
        return _spawn_script(script, log_path)

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
        **_kwargs: object,
    ) -> subprocess.Popen[str]:
        return _spawn_script(script, log_path)

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


def test_app_server_json_helpers_ignore_invalid_payloads() -> None:
    """App-server JSON parsing ignores non-object or malformed messages."""

    assert parse_app_server_line("not-json") is None
    assert parse_app_server_line("[]") is None
    assert parse_app_server_line(json.dumps({"id": "not-int"})) is None
    response = parse_app_server_line(
        json.dumps({"id": 9, "error": {"message": "boom"}}),
    )

    assert response is not None
    assert response.error == "boom"


def test_app_server_client_rejects_unaccepted_completion(tmp_path: Path) -> None:
    """Public client rejects completion before turn/start acceptance."""

    script = tmp_path / "unaccepted_completion.py"
    script.write_text(
        'import json\nprint(json.dumps({"method": "turn/completed"}), flush=True)\n'
        "for _line in __import__('sys').stdin:\n    pass\n",
        encoding="utf-8",
    )
    client = _client_for_script(script, timeout_seconds=1)

    with pytest.raises(RuntimeError, match="completed unaccepted turn"):
        client.resume_thread(THREAD_ID, "continue now")


def test_app_server_client_reports_early_exit_stderr(tmp_path: Path) -> None:
    """Public client surfaces bounded stderr when the server exits early."""

    script = tmp_path / "early_exit.py"
    script.write_text(
        "import sys\n"
        "for _index in range(4):\n    sys.stdin.readline()\n"
        "print('boom', file=sys.stderr, flush=True)\n",
        encoding="utf-8",
    )
    client = _client_for_script(script, timeout_seconds=1)

    with pytest.raises(RuntimeError, match="exited early: boom"):
        client.resume_thread(THREAD_ID, "continue now")


def test_app_server_client_times_out_while_server_is_quiet(tmp_path: Path) -> None:
    """Public client times out when the server remains quiet."""

    script = tmp_path / "quiet.py"
    script.write_text(
        "import sys, time\nfor _index in range(4):\n    sys.stdin.readline()\ntime.sleep(2)\n",
        encoding="utf-8",
    )
    client = _client_for_script(script, timeout_seconds=0.01)

    with pytest.raises(TimeoutError, match="rewake timed out"):
        client.resume_thread(THREAD_ID, "continue now")


def _client_for_script(script: Path, *, timeout_seconds: float) -> CodexAppServerClient:
    """Return a client backed by one fixture app-server script."""

    def popen_factory(
        _command: list[str],
        **_kwargs: object,
    ) -> subprocess.Popen[str]:
        return _spawn_script(script)

    return CodexAppServerClient(
        codex_bin="codex-test",
        timeout_seconds=timeout_seconds,
        popen_factory=popen_factory,
    )


def _spawn_script(script: Path, *arguments: Path) -> subprocess.Popen[str]:
    """Start a text-mode fixture app-server with the required pipes."""

    return subprocess.Popen(  # nosec B603
        [sys.executable, str(script), *(str(argument) for argument in arguments)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
