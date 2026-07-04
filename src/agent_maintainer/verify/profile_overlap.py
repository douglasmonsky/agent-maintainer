"""Advisory profile-overlap guardrails for verifier runs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from types import MappingProxyType

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.read import read_runtime_events

HEAVY_PROFILES = frozenset(("full", "ci", "security", "manual"))
OVERLAP_PARTNERS = MappingProxyType(
    {
        "full": "ci",
        "ci": "full",
        "security": "manual",
        "manual": "security",
    },
)
MIN_HEAVY_PROFILE_TYPES = 3


def profile_overlap_advisory(profile: str, config: MaintainerConfig) -> str:
    """Return advisory text for likely redundant profile validation."""
    if not config.runtime_events_enabled:
        return ""
    profiles = recent_finished_profiles(config)
    partner = OVERLAP_PARTNERS.get(profile)
    if partner and profiles[partner]:
        return partner_advisory(profile, partner)
    heavy_seen = sum(1 for heavy_profile in HEAVY_PROFILES if profiles[heavy_profile])
    if profile in HEAVY_PROFILES and heavy_seen >= MIN_HEAVY_PROFILE_TYPES - 1:
        return (
            f"`{profile}` adds a third heavy profile in the recent event window. "
            "Run several broad profiles only for release, gate, or profile-behavior changes."
        )
    return ""


def recent_finished_profiles(config: MaintainerConfig) -> Counter[str]:
    """Return profile.finished counts from the configured runtime-event window."""
    read_result = read_runtime_events(
        Path(config.runtime_events_dir),
        file_limit=config.runtime_event_history_limit,
    )
    return Counter(
        str(record.get("profile"))
        for record in read_result.records
        if record.get("event_name") == "profile.finished" and record.get("profile")
    )


def partner_advisory(profile: str, partner: str) -> str:
    """Return specific two-profile overlap advisory."""
    if {profile, partner} == {"full", "ci"}:
        return (
            f"Recent `{partner}` run found before `{profile}`. Use one broad local "
            "profile by default; run both only when verifier, profile, workflow, "
            "or diff/base behavior is under test."
        )
    return (
        f"Recent `{partner}` run found before `{profile}`. Reserve `security` plus "
        "`manual` for release work, gate changes, or explicit requests."
    )


def print_profile_overlap_advisory(message: str) -> None:
    """Print compact advisory when there is useful profile-overlap guidance."""
    if message:
        print("ADVISORY:")
        print(f"  profile-overlap: {message}")
