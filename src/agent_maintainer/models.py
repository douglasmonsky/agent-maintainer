"""Shared models for maintainer checks and results."""

from __future__ import annotations

from dataclasses import dataclass

FAST_PROFILE = "fast"
PRECOMMIT_PROFILE = "precommit"
FULL_PROFILE = "full"
CI_PROFILE = "ci"
SECURITY_PROFILE = "security"
MANUAL_PROFILE = "manual"

ALL_PROFILES = frozenset((FAST_PROFILE, PRECOMMIT_PROFILE, FULL_PROFILE, CI_PROFILE))
LOCAL_GATE_PROFILES = frozenset((PRECOMMIT_PROFILE, FULL_PROFILE, CI_PROFILE))
FULL_PROFILES = frozenset((FULL_PROFILE, CI_PROFILE))
CI_ONLY_PROFILES = frozenset((CI_PROFILE,))
MANUAL_PROFILES = frozenset((MANUAL_PROFILE,))
VALID_PROFILES = frozenset((*ALL_PROFILES, SECURITY_PROFILE, MANUAL_PROFILE))
SKIP_STATUS_DISABLED = "skipped-disabled"
SKIP_STATUS_MISSING_OPTIONAL = "skipped-missing-optional"
SKIP_STATUS_NOT_APPLICABLE = "skipped-not-applicable"
SKIP_STATUS_UNSAFE_CONFIG = "skipped-unsafe-config"
SKIP_STATUS_REQUIRED = "skipped-required"
SKIP_STATUSES = frozenset(
    (
        SKIP_STATUS_DISABLED,
        SKIP_STATUS_MISSING_OPTIONAL,
        SKIP_STATUS_NOT_APPLICABLE,
        SKIP_STATUS_UNSAFE_CONFIG,
        SKIP_STATUS_REQUIRED,
    )
)


@dataclass(frozen=True)
class Check:
    """Executable maintainer check plus the profiles where it should run."""

    name: str
    command: list[str]
    profiles: frozenset[str]
    required_paths: tuple[str, ...] = ()
    required_executable: str | None = None
    optional_skip_reason: str | None = None
    optional_skip_status: str = SKIP_STATUS_DISABLED
    report_success_output: bool = False
    artifact_paths: tuple[str, ...] = ()
    timeout_seconds: int | None = None
    output_limit_chars: int | None = None
    artifact_sensitivity: str = "safe"
    structured_parser: str = ""
    structured_parser_manager: str = ""


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one maintainer check after execution or optional skipping."""

    name: str
    passed: bool
    output: str = ""
    skipped: bool = False
    skip_status: str = ""
    warning: bool = False
    command: tuple[str, ...] = ()
    exit_code: int | None = None
    log_path: str = ""
    started_at: str = ""
    ended_at: str = ""
    artifact_paths: tuple[str, ...] = ()
    artifact_sensitivity: str = "safe"
    structured_parser: str = ""
    structured_parser_manager: str = ""
