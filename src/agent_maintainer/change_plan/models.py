"""Models for cohesive change plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

PLAN_DIR = Path(".agent-maintainer/change-plans")
PLAN_SUFFIX = ".md"
FRONT_MATTER_DELIMITER = "+++"
ACTIVE_STATUS = "active"
REQUIRED_SECTIONS = (
    "Why this change intentionally large",
    "Why this should not be split smaller",
    "What allowed to change",
    "What must not change",
    "Verification plan",
    "Rollback plan",
    "Follow-up ratchet work",
)


@dataclass(frozen=True)
class PlanMetadata:
    """Structured TOML metadata for one cohesive change plan."""

    id: str
    kind: str
    status: str
    base_ref: str
    expires: date
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    max_changed_files: int
    max_changed_lines: int
    allow_source_without_test_change: bool
    requires_tests: bool
    requires_full_verify: bool
    ratchet_targets: tuple[str, ...]
    integration_branch: str = ""
    target_branch: str = ""
    merge_strategy: str = ""
    expected_units: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangePlan:
    """Parsed cohesive change plan."""

    path: Path
    metadata: PlanMetadata
    body: str
    sections: dict[str, str]


@dataclass(frozen=True)
class ValidationIssue:
    """One change-plan validation issue."""

    path: str
    message: str


@dataclass(frozen=True)
class ChangedPath:
    """One changed path with numstat counts."""

    path: str
    added: int
    deleted: int

    @property
    def changed_lines(self) -> int:
        """Return added plus deleted line count."""

        return self.added + self.deleted
