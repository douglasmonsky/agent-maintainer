"""Private state files for repo wait daemon."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

from agent_maintainer.wait.codex_rewake import (
    CODEX_APP_SERVER_TIMEOUT_ENV,
    CODEX_BIN_ENV,
    CODEX_REWAKE_ENV,
    CODEX_THREAD_ID_ENV,
    CODEX_THREAD_ID_OVERRIDE_ENV,
)

ENVELOPE_TTL_SECONDS: Final = 3600
WATCHERS_DIR_NAME: Final = "watchers"
DAEMON_LOG_NAME: Final = "daemon.log"
DAEMON_HEARTBEAT_NAME: Final = "daemon-heartbeat.json"
ENVELOPE_NAME: Final = "rewake-env.json"
ENVELOPE_MODE: Final = 0o600


def write_rewake_envelope(
    root: Path,
    wait_id: str,
    env: Mapping[str, str],
    *,
    ttl_seconds: int = ENVELOPE_TTL_SECONDS,
) -> Path:
    """Write private short-lived env used only by daemon rewake."""

    thread_id = _thread_id(env)
    if not thread_id:
        raise RuntimeError("Codex thread id unavailable")
    payload = {
        "created_at": _timestamp(),
        "expires_at": _timestamp(timedelta(seconds=ttl_seconds)),
        "env": _rewake_env(env, thread_id),
    }
    path = rewake_envelope_path(root, wait_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    path.chmod(ENVELOPE_MODE)
    return path


def read_rewake_envelope(root: Path, wait_id: str) -> dict[str, str] | None:
    """Read and delete private rewake envelope."""

    path = rewake_envelope_path(root, wait_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return None
    finally:
        path.unlink(missing_ok=True)
    if not isinstance(payload, dict) or _expired(payload):
        return None
    value = payload.get("env")
    if not isinstance(value, dict):
        return None
    return {str(key): str(item) for key, item in value.items()}


def has_rewake_envelope(root: Path, wait_id: str) -> bool:
    """Return whether wait has a non-expired rewake envelope."""

    path = rewake_envelope_path(root, wait_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    if not isinstance(payload, dict) or _expired(payload):
        path.unlink(missing_ok=True)
        return False
    return True


def rewake_envelope_path(root: Path, wait_id: str) -> Path:
    """Return private rewake envelope path for one wait."""

    return watchers_dir(root) / wait_id / ENVELOPE_NAME


def watchers_dir(root: Path) -> Path:
    """Return repo watcher state directory."""

    return root / ".verify-logs" / WATCHERS_DIR_NAME


def daemon_log_path(root: Path) -> Path:
    """Return repo wait daemon log path."""

    return watchers_dir(root) / DAEMON_LOG_NAME


def write_heartbeat(root: Path, *, summary_checked: int, resumed: int) -> None:
    """Write compact daemon heartbeat metadata."""

    path = watchers_dir(root) / DAEMON_HEARTBEAT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "updated_at": _timestamp(),
                "pid": os.getpid(),
                "checked": summary_checked,
                "resumed": resumed,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def read_heartbeat(root: Path) -> str:
    """Read latest daemon heartbeat timestamp."""

    try:
        payload = json.loads((watchers_dir(root) / DAEMON_HEARTBEAT_NAME).read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("updated_at", ""))


def _rewake_env(env: Mapping[str, str], thread_id: str) -> dict[str, str]:
    output = {
        CODEX_REWAKE_ENV: env.get(CODEX_REWAKE_ENV, ""),
        CODEX_THREAD_ID_OVERRIDE_ENV: thread_id,
        CODEX_BIN_ENV: env.get(CODEX_BIN_ENV, ""),
        CODEX_APP_SERVER_TIMEOUT_ENV: env.get(CODEX_APP_SERVER_TIMEOUT_ENV, ""),
    }
    return {key: value for key, value in output.items() if value}


def _thread_id(env: Mapping[str, str]) -> str:
    return env.get(CODEX_THREAD_ID_OVERRIDE_ENV) or env.get(CODEX_THREAD_ID_ENV, "")


def _timestamp(delta: timedelta | None = None) -> str:
    value = datetime.now(UTC)
    if delta is not None:
        value += delta
    return value.isoformat().replace("+00:00", "Z")


def _expired(payload: Mapping[str, object]) -> bool:
    expires_at = payload.get("expires_at")
    if not isinstance(expires_at, str):
        return True
    expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    return datetime.now(UTC) >= expires
