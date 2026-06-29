"""Read bounded failure context from verifier artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_maintainer.context.budget import bound_text
from agent_maintainer.context.models import ContextBudget
from agent_maintainer.verify.artifacts import MANIFEST_NAME

DEFAULT_FAILURE_LIMIT = 20
DEFAULT_CONTEXT_BUDGET = 12_000
FAILURE_STATUSES = frozenset(("failed",))


@dataclass(frozen=True)
class FailureCategoryRule:
    """Rule assigning a failed check to a repair category."""

    category: str
    priority: int
    tokens: tuple[str, ...]


FAILURE_CATEGORY_RULES = (
    FailureCategoryRule("tool/config", 1, ("bootstrap", "doctor", "config", "install")),
    FailureCategoryRule("syntax/import", 2, ("syntax", "import")),
    FailureCategoryRule("type", 3, ("pyright", "mypy")),
    FailureCategoryRule("test", 4, ("pytest", "test")),
    FailureCategoryRule("coverage", 5, ("coverage", "diff-cover")),
    FailureCategoryRule("architecture", 6, ("tach", "import-linter", "arch")),
    FailureCategoryRule("structure-ratchet", 7, ("file-length", "structure", "ratchet")),
    FailureCategoryRule("suppression", 8, ("suppression",)),
    FailureCategoryRule("security/tooling", 9, ("bandit", "audit", "secret", "semgrep", "zizmor")),
)
DEFAULT_FAILURE_CATEGORY = FailureCategoryRule("style/noise", 10, ())


@dataclass(frozen=True)
class FailureRecord:
    """One failed check from a verifier manifest."""

    name: str
    status: str
    category: str
    priority: int
    exit_code: int | None
    log_path: str
    log_bytes: int
    expansion_commands: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        """Return stable JSON payload."""

        return {
            "name": self.name,
            "status": self.status,
            "category": self.category,
            "priority": self.priority,
            "exit_code": self.exit_code,
            "log_path": self.log_path,
            "log_bytes": self.log_bytes,
            "expansion_commands": list(self.expansion_commands),
        }


def manifest_path(log_dir: Path) -> Path:
    """Return verifier manifest path."""

    return log_dir / MANIFEST_NAME


def load_manifest(log_dir: Path) -> dict[str, Any] | None:
    """Load manifest JSON when present and valid."""

    path = manifest_path(log_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def failure_records(
    log_dir: Path,
    *,
    check_name: str | None = None,
    limit: int = DEFAULT_FAILURE_LIMIT,
) -> tuple[FailureRecord, ...]:
    """Return failed checks from manifest sorted by repair priority."""

    manifest = load_manifest(log_dir)
    if manifest is None:
        return ()
    checks = manifest.get("checks", [])
    if not isinstance(checks, list):
        return ()
    records = [
        record
        for item in checks
        if (record := record_from_payload(item)) is not None
        and record.status in FAILURE_STATUSES
        and (check_name is None or record.name == check_name)
    ]
    return tuple(sorted(records, key=record_sort_key)[:limit])


def record_from_payload(payload: object) -> FailureRecord | None:
    """Return failure record from manifest check payload."""

    if not isinstance(payload, dict):
        return None
    name = str(payload.get("name", "unknown"))
    status = str(payload.get("status", "unknown"))
    category, priority = failure_category(name)
    return FailureRecord(
        name=name,
        status=status,
        category=category,
        priority=priority,
        exit_code=optional_int(payload.get("exit_code")),
        log_path=str(payload.get("log_path", "")),
        log_bytes=optional_int(payload.get("log_bytes")) or 0,
        expansion_commands=string_tuple(payload.get("expansion_commands", [])),
    )


def optional_int(value: object) -> int | None:
    """Return int when value is integer-like."""

    return value if isinstance(value, int) else None


def string_tuple(value: object) -> tuple[str, ...]:
    """Return tuple of strings from JSON value."""

    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def failure_category(check_name: str) -> tuple[str, int]:
    """Return human category and priority for a failed check."""

    name = check_name.lower()
    rule = next(
        (
            candidate
            for candidate in FAILURE_CATEGORY_RULES
            if any(token in name for token in candidate.tokens)
        ),
        DEFAULT_FAILURE_CATEGORY,
    )
    return (rule.category, rule.priority)


def record_sort_key(record: FailureRecord) -> tuple[int, str]:
    """Return stable failure sorting key."""

    return (record.priority, record.name)


def render_failures_text(
    records: tuple[FailureRecord, ...],
    *,
    log_dir: Path,
    budget: int = DEFAULT_CONTEXT_BUDGET,
) -> str:
    """Return bounded text failure report."""

    if not manifest_path(log_dir).exists():
        return f"No verifier manifest found at {manifest_path(log_dir)}."
    if not records:
        return "No failed checks found in verifier manifest."
    lines = ["Context failures", ""]
    for index, record in enumerate(records, start=1):
        lines.extend(render_record(index, record))
    return bound_report("\n".join(lines).rstrip(), budget)


def render_record(index: int, record: FailureRecord) -> list[str]:
    """Return text lines for one failure record."""

    log_path = record.log_path or "<none>"
    lines = [
        f"{index}. {record.name}",
        f"   category: {record.category}",
        f"   status: {record.status}",
        f"   exit code: {record.exit_code}",
        f"   log: {log_path}",
        f"   log bytes: {record.log_bytes}",
    ]
    if record.expansion_commands:
        lines.append("   expansion commands:")
        lines.extend(f"   - {command}" for command in record.expansion_commands)
    return [*lines, ""]


def bound_report(text: str, budget: int) -> str:
    """Return text bounded by context budget."""

    bounded = bound_text(text, ContextBudget(max_chars=budget, max_items=1))
    if not bounded.truncated:
        return bounded.text
    return "\n".join(
        (
            bounded.text.rstrip(),
            (
                "... context failures omitted "
                f"{bounded.omitted_chars} chars and {bounded.omitted_lines} lines."
            ),
        )
    )


def render_failures_json(records: tuple[FailureRecord, ...], *, log_dir: Path) -> str:
    """Return stable JSON failure report."""

    payload = {
        "manifest_path": str(manifest_path(log_dir)),
        "failures": [record.to_json() for record in records],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
