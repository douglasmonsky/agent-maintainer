"""Background wait registration for verifier launches."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from agent_maintainer.wait import broker as lifecycle_broker
from agent_waits import broker as wait_broker

VERIFIER_WAIT_INTERVAL_SECONDS: Final = 5
VERIFIER_WAIT_TIMEOUT_SECONDS: Final = 3600


def register_background_verifier_wait(
    run_id: str,
    log_dir: Path,
) -> wait_broker.BackgroundWaitRegistration:
    """Register one verifier wait through the canonical durable lifecycle."""

    return lifecycle_broker.register_background_verifier(
        lifecycle_broker.BackgroundVerifierWait(
            root=Path.cwd(),
            run_id=run_id,
            platform=wait_broker.CODEX_PLATFORM,
            log_dir=log_dir,
            interval_seconds=VERIFIER_WAIT_INTERVAL_SECONDS,
            timeout_seconds=VERIFIER_WAIT_TIMEOUT_SECONDS,
        )
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
