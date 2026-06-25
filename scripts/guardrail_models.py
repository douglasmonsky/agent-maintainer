"""Shared models for guardrail checks and results."""

from __future__ import annotations

from dataclasses import dataclass

FAST_PROFILE = "fast"
PRECOMMIT_PROFILE = "precommit"
FULL_PROFILE = "full"
CI_PROFILE = "ci"

ALL_PROFILES = frozenset({FAST_PROFILE, PRECOMMIT_PROFILE, FULL_PROFILE, CI_PROFILE})
LOCAL_GATE_PROFILES = frozenset({PRECOMMIT_PROFILE, FULL_PROFILE, CI_PROFILE})
FULL_PROFILES = frozenset({FULL_PROFILE, CI_PROFILE})
CI_ONLY_PROFILES = frozenset({CI_PROFILE})


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    profiles: frozenset[str]
    required_paths: tuple[str, ...] = ()
    required_executable: str | None = None
    optional_skip_reason: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    output: str = ""
    skipped: bool = False
