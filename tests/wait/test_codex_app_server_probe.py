"""Tests read-only Codex app-server probing."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from agent_maintainer.wait.codex_app_server import CodexAppServerClient

THREAD_ID = "thread-1"


def test_app_server_client_runs_read_only_thread_probe(tmp_path: Path) -> None:
    """Read-only smoke sends initialize and thread/read without turn/start."""

    script = tmp_path / "fake_app_server_probe.py"
    log_path = tmp_path / "probe-messages.jsonl"
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
            print(json.dumps({"id": request_id, "result": {"thread": {}}}), flush=True)
        if message.get("method") == "thread/read":
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
    )

    client.probe_thread(THREAD_ID)

    methods = [
        message["method"]
        for message in (
            json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert methods == ["initialize", "initialized", "thread/read"]
