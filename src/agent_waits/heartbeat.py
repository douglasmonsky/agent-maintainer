"""Generic wait heartbeat metadata helpers."""

from __future__ import annotations

from typing import Final

HEARTBEAT_MODE_METADATA: Final = "heartbeat_mode"
HEARTBEAT_MODE_REPO: Final = "repo"
HEARTBEAT_NOTIFIED_AT_METADATA: Final = "heartbeat_notified_at"


def registration_metadata(
    metadata: dict[str, object] | None,
) -> dict[str, object]:
    """Return persisted metadata for a newly registered wait."""

    current = dict(metadata or {})
    current.setdefault(HEARTBEAT_MODE_METADATA, HEARTBEAT_MODE_REPO)
    return current


def repo_heartbeat_ready(metadata: dict[str, object] | None) -> bool:
    """Return whether a ready wait should notify a repo heartbeat."""

    current = metadata or {}
    return (
        current.get(HEARTBEAT_MODE_METADATA) == HEARTBEAT_MODE_REPO
        and HEARTBEAT_NOTIFIED_AT_METADATA not in current
    )
