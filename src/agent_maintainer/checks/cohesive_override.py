"""Validate rare cohesive-change overrides for change-budget failures."""

from __future__ import annotations

import fnmatch
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_maintainer.config.schema import MaintainerConfig

OVERRIDE_SECTION_PATTERN = re.compile(
    r"(?ims)^#{2,6}\s*cohesive-change override\s*$"
    r"(?P<section>.*?)(?=^#{2,6}\s|\Z)",
)
TRUTHY_VALUES = frozenset(("1", "true", "yes", "y", "on"))
REQUEST_LABEL = "Override requested"
REQUIRED_LABELS = (
    "Why this is one cohesive unit",
    "Why smaller PRs would make the repository less coherent",
    "Tests/verification proving behavior is unchanged",
    "Behavior change",
)
UNCHANGED_MARKERS = ("none", "unchanged", "no behavior", "not intended")


class ChangedFile(Protocol):
    """Protocol for change-budget file summaries."""

    @property
    def path(self) -> str:
        """Return changed path."""
        raise NotImplementedError

    @property
    def changed(self) -> int:
        """Return total changed lines."""
        raise NotImplementedError


@dataclass(frozen=True)
class OverrideDecision:
    """Decision for whether a cohesive-change override may bypass hard budgets."""

    requested: bool
    allowed: bool
    failures: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def evaluate_override(
    config: MaintainerConfig,
    changes: Sequence[ChangedFile],
) -> OverrideDecision:
    """Return cohesive-change override decision for current diff context."""

    request = current_override_request()
    if not request.requested:
        return OverrideDecision(requested=False, allowed=False)

    failures = list(eligibility_failures(config, changes))
    failures.extend(request.failures)
    if failures:
        return OverrideDecision(requested=True, allowed=False, failures=tuple(failures))

    warnings = (
        "Cohesive-change override accepted; CI must still review the PR explanation."
        if request.source == "github-pr"
        else (
            "Cohesive-change override requested locally; GitHub CI must verify the "
            "required PR explanation before merge."
        )
    )
    return OverrideDecision(requested=True, allowed=True, warnings=(warnings,))


@dataclass(frozen=True)
class OverrideRequest:
    """Parsed override request from GitHub PR context or explicit local env."""

    requested: bool
    source: str
    failures: tuple[str, ...] = ()


def current_override_request() -> OverrideRequest:
    """Return override request from GitHub PR body or local explicit env."""

    pr_body = github_pr_body()
    if pr_body is not None:
        return parse_pr_body(pr_body)
    if local_override_requested():
        return OverrideRequest(requested=True, source="local-env")
    return OverrideRequest(requested=False, source="none")


def local_override_requested() -> bool:
    """Return whether local environment explicitly asks for override handling."""

    value = os.getenv("AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED", "")
    return value.strip().lower() in TRUTHY_VALUES


def github_pr_body() -> str | None:
    """Return GitHub pull request body when running in a PR workflow."""

    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    if event_name not in {"pull_request", "pull_request_target"}:
        return None
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    path = Path(event_path)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    body = pull_request.get("body")
    return body if isinstance(body, str) else ""


def parse_pr_body(body: str) -> OverrideRequest:
    """Parse cohesive-change override metadata from PR body."""

    section = override_section(body)
    if section is None:
        return OverrideRequest(requested=False, source="github-pr")

    requested = field_value(section, REQUEST_LABEL).lower()
    if requested not in TRUTHY_VALUES:
        return OverrideRequest(requested=False, source="github-pr")

    failures = list(required_field_failures(section))
    behavior = field_value(section, "Behavior change").lower()
    if behavior and not any(marker in behavior for marker in UNCHANGED_MARKERS):
        failures.append("Cohesive-change override must state behavior is unchanged.")
    return OverrideRequest(requested=True, source="github-pr", failures=tuple(failures))


def override_section(body: str) -> str | None:
    """Return cohesive-change override section body if present."""

    match = OVERRIDE_SECTION_PATTERN.search(body)
    return match.group("section") if match else None


def required_field_failures(section: str) -> tuple[str, ...]:
    """Return missing required explanation field failures."""

    failures = [
        f"Cohesive-change override missing required field: {label}."
        for label in REQUIRED_LABELS
        if not useful_field_value(field_value(section, label))
    ]
    return tuple(failures)


def field_value(section: str, label: str) -> str:
    """Return inline markdown field value for one label."""

    pattern = re.compile(rf"(?im)^\s*(?:[-*]\s*)?{re.escape(label)}\s*:\s*(?P<value>.+?)\s*$")
    match = pattern.search(section)
    return match.group("value").strip() if match else ""


def useful_field_value(value: str) -> bool:
    """Return whether field value contains real explanatory text."""

    normalized = value.strip().lower()
    return bool(normalized) and normalized not in {"n/a", "na", "none", "todo", "tbd"}


def eligibility_failures(
    config: MaintainerConfig,
    changes: Sequence[ChangedFile],
) -> tuple[str, ...]:
    """Return config, path, and maximum-size override eligibility failures."""

    failures: list[str] = []
    if not config.cohesive_change_override_enabled:
        failures.append("Cohesive-change overrides are disabled for this repository.")
    if not config.cohesive_change_override_paths:
        failures.append("Cohesive-change override has no configured path allowlist.")

    total_lines = sum(change.changed for change in changes)
    total_files = len(changes)
    if total_lines > config.cohesive_change_override_max_lines:
        failures.append(
            "Cohesive-change override exceeds maximum size: "
            f"{total_lines} changed lines "
            f"(limit: {config.cohesive_change_override_max_lines})."
        )
    if total_files > config.cohesive_change_override_max_files:
        failures.append(
            "Cohesive-change override touches too many files: "
            f"{total_files} files (limit: {config.cohesive_change_override_max_files})."
        )

    outside_allowlist = [
        change.path
        for change in changes
        if not path_allowed(change.path, config.cohesive_change_override_paths)
    ]
    if outside_allowlist:
        failures.append(
            "Cohesive-change override includes paths outside the allowlist: "
            + ", ".join(outside_allowlist)
            + "."
        )
    return tuple(failures)


def path_allowed(path: str, patterns: tuple[str, ...]) -> bool:
    """Return whether path matches a configured override allowlist pattern."""

    normalized = path.replace("\\", "/").lstrip("./")
    return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in patterns)
