"""Parse cohesive change plan markdown files."""

from __future__ import annotations

import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from agent_maintainer.change_plan.models import (
    FRONT_MATTER_DELIMITER,
    ChangePlan,
    PlanMetadata,
)

HEADING_PATTERN = re.compile(r"(?m)^#{1,6}\s+(?P<title>.+?)\s*$")


class PlanParseError(ValueError):
    """Raised when a cohesive change plan cannot be parsed."""


def parse_plan(path: Path) -> ChangePlan:
    """Parse a change plan from disk."""

    return parse_plan_text(path.read_text(encoding="utf-8"), path=path)


def parse_plan_text(text: str, *, path: Path) -> ChangePlan:
    """Parse a change plan from text."""

    front_matter, body = split_front_matter(text, path=path)
    raw_metadata = parse_metadata(front_matter, path=path)
    return ChangePlan(
        path=path,
        metadata=metadata_from_raw(raw_metadata, path=path),
        body=body,
        sections=parse_sections(body),
    )


def split_front_matter(text: str, *, path: Path) -> tuple[str, str]:
    """Return TOML front matter and markdown body."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_DELIMITER:
        raise PlanParseError(f"{path}: missing opening {FRONT_MATTER_DELIMITER}")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONT_MATTER_DELIMITER:
            front_matter = "\n".join(lines[1:index])
            body_start = index + 1
            body = "\n".join(lines[body_start:]).strip()
            return front_matter, body
    raise PlanParseError(f"{path}: missing closing {FRONT_MATTER_DELIMITER}")


def parse_metadata(front_matter: str, *, path: Path) -> dict[str, Any]:
    """Parse TOML front matter."""

    try:
        data = tomllib.loads(front_matter)
    except tomllib.TOMLDecodeError as exc:
        raise PlanParseError(f"{path}: invalid TOML front matter: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanParseError(f"{path}: front matter must be a TOML table")
    return data


def metadata_from_raw(raw: dict[str, Any], *, path: Path) -> PlanMetadata:
    """Return typed metadata from parsed TOML."""

    try:
        return PlanMetadata(
            id=required_str(raw, "id"),
            kind=required_str(raw, "kind"),
            status=required_str(raw, "status"),
            base_ref=required_str(raw, "base_ref"),
            expires=required_date(raw, "expires"),
            allowed_paths=string_tuple(raw.get("allowed_paths", ())),
            forbidden_paths=string_tuple(raw.get("forbidden_paths", ())),
            max_changed_files=required_int(raw, "max_changed_files"),
            max_changed_lines=required_int(raw, "max_changed_lines"),
            allow_source_without_test_change=required_bool(raw, "allow_source_without_test_change"),
            requires_tests=required_bool(raw, "requires_tests"),
            requires_full_verify=required_bool(raw, "requires_full_verify"),
            ratchet_targets=string_tuple(raw.get("ratchet_targets", ())),
            integration_branch=optional_str(raw, "integration_branch"),
            target_branch=optional_str(raw, "target_branch"),
            merge_strategy=optional_str(raw, "merge_strategy"),
            expected_units=string_tuple(raw.get("expected_units", ())),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise PlanParseError(f"{path}: invalid plan metadata: {exc}") from exc


def required_str(raw: dict[str, Any], key: str) -> str:
    """Return required non-empty string metadata."""

    value = raw[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def optional_str(raw: dict[str, Any], key: str) -> str:
    """Return optional stripped string metadata."""

    value = raw.get(key, "")
    if value == "":
        return ""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def required_int(raw: dict[str, Any], key: str) -> int:
    """Return required positive integer metadata."""

    value = raw[key]
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def required_bool(raw: dict[str, Any], key: str) -> bool:
    """Return required boolean metadata."""

    value = raw[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def required_date(raw: dict[str, Any], key: str) -> date:
    """Return required date metadata."""

    value = raw[key]
    if not isinstance(value, date):
        raise ValueError(f"{key} must be a TOML date")
    return value


def string_tuple(value: object) -> tuple[str, ...]:
    """Return tuple of non-empty strings from TOML array metadata."""

    if not isinstance(value, list | tuple):
        raise TypeError("path lists must be arrays")
    result = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(result) != len(value):
        raise ValueError("path lists must contain only non-empty strings")
    return result


def parse_sections(body: str) -> dict[str, str]:
    """Return markdown sections keyed by normalized title."""

    matches = list(HEADING_PATTERN.finditer(body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        title = normalized_heading(match.group("title"))
        sections[title] = body[start:end].strip()
    return sections


def normalized_heading(value: str) -> str:
    """Return normalized markdown heading for section matching."""

    return " ".join(value.strip().lower().split())
