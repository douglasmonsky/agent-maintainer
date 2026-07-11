"""Background wait registration for verifier launches."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Final

from agent_waits import broker as wait_broker
from agent_waits.registry import RegisterWait, WaitRegistry

VERIFIER_WAIT_KIND: Final = "verifier"
VERIFIER_LOG_DIR_METADATA: Final = "log_dir"
VERIFIER_WAIT_INTERVAL_SECONDS: Final = 5
VERIFIER_WAIT_TIMEOUT_SECONDS: Final = 3600


def register_background_verifier_wait(
    run_id: str,
    log_dir: Path,
) -> wait_broker.BackgroundWaitRegistration:
    """Register one verifier wait and start its detached watcher."""

    root = Path.cwd()
    record = WaitRegistry(root).register(
        RegisterWait(
            root=root,
            kind=VERIFIER_WAIT_KIND,
            target_id=run_id,
            platform=wait_broker.CODEX_PLATFORM,
            interval_seconds=VERIFIER_WAIT_INTERVAL_SECONDS,
            timeout_seconds=VERIFIER_WAIT_TIMEOUT_SECONDS,
            metadata={VERIFIER_LOG_DIR_METADATA: str(log_dir)},
        ),
    )
    watcher_started, watcher_error = start_wait_watcher(root, record.wait_id)
    return wait_broker.BackgroundWaitRegistration(
        record=record,
        watcher_started=watcher_started,
        watcher_error=watcher_error,
        root=str(root),
    )


def background_launch_enabled() -> bool:
    """Return whether async verifier launch should register a wait."""

    return (
        wait_broker.running_in_codex()
        and wait_broker.codex_background_wait_enabled()
        and not wait_broker.codex_foreground_wait_allowed()
    )


def render_background_registration_text(
    registration: wait_broker.BackgroundWaitRegistration,
) -> str:
    """Render compact background wait registration handoff."""

    return wait_broker.render_background_registration_text(registration)


def start_wait_watcher(root: Path, wait_id: str) -> tuple[bool, str]:
    """Start detached local watcher process for one wait record."""

    command = (
        sys.executable,
        "-m",
        "agent_maintainer",
        "wait",
        "sweep",
        "--watch",
        wait_id,
        "--root",
        str(root),
    )
    try:
        subprocess.Popen(  # nosec B603 # pylint: disable=consider-using-with
            list(command),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
    except OSError as exc:
        return False, str(exc)
    return True, ""
