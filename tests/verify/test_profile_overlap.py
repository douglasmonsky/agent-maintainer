"""Tests verifier profile-overlap advisories."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.verify.profile_overlap import profile_overlap_advisory


def event_config(tmp_path: Path) -> MaintainerConfig:
    """Return config with runtime events enabled in temp directory."""
    return MaintainerConfig(
        runtime_events_enabled=True,
        runtime_events_dir=str(tmp_path),
        runtime_event_history_limit=5,
    )


def write_profile_event(events_dir: Path, profile: str, *, name: str = "events.jsonl") -> None:
    """Append one completed profile event."""
    events_dir.mkdir(parents=True, exist_ok=True)
    event_path = events_dir / name
    payload = {"event_name": "profile.finished", "profile": profile}
    with event_path.open("a", encoding="utf-8") as event_file:
        event_file.write(f"{json.dumps(payload)}\n")


def test_disabled_without_events(tmp_path: Path) -> None:
    """No advisory is emitted when runtime-event storage is disabled."""
    write_profile_event(tmp_path, "full")

    message = profile_overlap_advisory(
        "ci",
        MaintainerConfig(runtime_events_enabled=False, runtime_events_dir=str(tmp_path)),
    )

    assert message == ""


def test_warns_for_full_ci_pair(tmp_path: Path) -> None:
    """Running full and ci together produces compact advisory."""
    write_profile_event(tmp_path, "full")

    message = profile_overlap_advisory("ci", event_config(tmp_path))

    assert "Recent `full` run found before `ci`" in message
    assert "run both only when" in message


def test_warns_for_security_manual_pair(tmp_path: Path) -> None:
    """Running security and manual together produces compact advisory."""
    write_profile_event(tmp_path, "manual")

    message = profile_overlap_advisory("security", event_config(tmp_path))

    assert "Recent `manual` run found before `security`" in message
    assert "explicit requests" in message


def test_warns_for_third_heavy(tmp_path: Path) -> None:
    """Three heavy profiles in one event window get a stronger advisory."""
    write_profile_event(tmp_path, "ci")
    write_profile_event(tmp_path, "manual")

    message = profile_overlap_advisory("ci", event_config(tmp_path))

    assert "`ci` adds a third heavy profile" in message


def test_ignores_unrelated_profiles(tmp_path: Path) -> None:
    """Normal precommit to ci cadence does not produce overlap advisory."""
    write_profile_event(tmp_path, "precommit")

    message = profile_overlap_advisory("ci", event_config(tmp_path))

    assert message == ""
