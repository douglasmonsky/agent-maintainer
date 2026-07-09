"""Tests Codex app-server accepted-turn lifecycle."""

from __future__ import annotations

import json
import subprocess
from io import StringIO
from typing import Any, cast

from agent_maintainer.wait.codex_app_server import CodexAppServerClient

THREAD_ID = "thread-1"


def test_app_server_client_detaches_after_turn_acceptance() -> None:
    """Acceptance handoff leaves the app-server process alive."""

    process = AcceptedTurnProcess()

    def popen_factory(
        _command: list[str],
        **_kwargs: Any,
    ) -> subprocess.Popen[str]:
        return cast(subprocess.Popen[str], process)

    client = CodexAppServerClient(
        codex_bin="codex-test",
        timeout_seconds=5,
        popen_factory=popen_factory,
        return_after_turn_acceptance=True,
    )

    client.resume_thread(THREAD_ID, "continue now")

    assert not process.terminated
    assert process.stdin is not None
    assert process.stdin.closed


class AcceptedTurnProcess:
    """Process double that accepts turn/start and must not be terminated."""

    def __init__(self) -> None:
        self.stdin: StringIO | None = StringIO()
        self.stdout: StringIO | None = StringIO(_accepted_turn_output())
        self.stderr: StringIO | None = StringIO()
        self.terminated = False

    def poll(self) -> int | None:
        """Return running process state."""

        return None

    def terminate(self) -> None:
        """Fail if acceptance handoff terminates the child process."""

        self.terminated = True
        raise AssertionError("accepted app-server process was terminated")

    def wait(self, timeout: float | None = None) -> int:
        """Detached process can be reaped by the drainer thread."""

        return 0


def _accepted_turn_output() -> str:
    return "\n".join(
        (
            json.dumps({"id": 1, "result": {}}),
            json.dumps({"id": 2, "result": {}}),
            json.dumps({"id": 3, "result": {"turn": {"id": "turn-1", "status": "inProgress"}}}),
        )
    )
