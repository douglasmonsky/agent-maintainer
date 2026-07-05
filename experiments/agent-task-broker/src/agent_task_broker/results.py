"""Structured task result validation for broker handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STATUS_DONE = "done"
STATUS_BLOCKED = "blocked"
STATUS_ESCALATE = "escalate"
STATUS_ABANDONED = "abandoned"
RESULT_STATUSES = (STATUS_DONE, STATUS_BLOCKED, STATUS_ESCALATE, STATUS_ABANDONED)


@dataclass(frozen=True)
class ResultInput:
    """Structured result input."""

    root: Path
    task_id: str
    status: str
    summary: str = ""
    verification: tuple[str, ...] = ()
    needs: tuple[str, ...] = ()
    reason: str = ""
    changed_files: tuple[str, ...] = ()


class ResultError(ValueError):
    """Structured result is invalid."""


def result_payload(inputs: ResultInput) -> dict[str, object]:
    """Return validated result payload."""
    payload = {
        "task_id": inputs.task_id,
        "status": inputs.status,
        "summary": inputs.summary,
        "verification": list(inputs.verification),
        "needs": list(inputs.needs),
        "reason": inputs.reason,
        "changed_files": normalize_changed_files(
            inputs.root,
            list(inputs.changed_files),
        ),
    }
    validate_result(payload)
    return payload


def validate_result(payload: dict[str, object]) -> None:
    """Validate structured task result status requirements."""
    status = payload.get("status")
    if status not in RESULT_STATUSES:
        raise ResultError(f"unknown result status: {status}")
    if status == STATUS_DONE and not payload.get("verification"):
        raise ResultError("done result requires at least one verification entry")
    if status == STATUS_BLOCKED and not payload.get("needs"):
        raise ResultError("blocked result requires at least one need")
    if status in {STATUS_ESCALATE, STATUS_ABANDONED} and not payload.get("reason"):
        raise ResultError(f"{status} result requires a reason")


def normalize_changed_files(root: Path, paths: list[str]) -> list[str]:
    """Return changed file paths normalized relative to repo root."""
    return [normalize_repo_path(root, path) for path in paths]


def normalize_repo_path(root: Path, path: str) -> str:
    """Return one normalized repo-relative path."""
    candidate = Path(path)
    if candidate.is_absolute():
        return absolute_repo_path(root, candidate)
    normalized = candidate.as_posix()
    if normalized.startswith("../") or normalized == "..":
        raise ResultError(f"changed file escapes repository: {path}")
    return normalized


def absolute_repo_path(root: Path, path: Path) -> str:
    """Return absolute path as repo-relative path."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ResultError(f"changed file escapes repository: {path}") from exc
