"""Extract exact repair facts from verifier artifacts."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from agent_maintainer.context.failures import FailureRecord
from agent_repair_facts import registry as fact_parsers
from agent_repair_facts.payloads import fact_payload

MAX_FACTS_PER_CHECK = 5
PYTEST_ARTIFACT_PRIORITY = MappingProxyType(
    {
        "pytest-junit.xml": 0,
        "coverage.json": 1,
    },
)


def repair_facts(log_dir: Path, records: tuple[FailureRecord, ...]) -> list[dict[str, object]]:
    """Return bounded exact repair facts for failed checks."""

    facts: list[dict[str, object]] = []
    for record in records:
        extracted = structured_facts(log_dir, record)
        facts.extend(extracted[:MAX_FACTS_PER_CHECK] or [generic_fact(record)])
    return facts


def structured_facts(log_dir: Path, record: FailureRecord) -> list[dict[str, object]]:
    """Return facts extracted from known artifacts and logs."""

    artifact_facts = [
        fact
        for artifact_path in artifact_paths_for(record)
        for fact in fact_parsers.artifact_facts(
            record.name,
            resolved_artifact_path(log_dir, artifact_path),
        )
    ]
    if artifact_facts:
        return artifact_facts
    return fact_parsers.log_facts(record.name, resolved_log_path(log_dir, record.log_path))


def artifact_paths_for(record: FailureRecord) -> tuple[str, ...]:
    """Return artifact paths ordered by usefulness for exact facts."""

    if record.name != "pytest-coverage":
        return record.artifact_paths
    return tuple(sorted(record.artifact_paths, key=pytest_artifact_priority))


def pytest_artifact_priority(artifact_path: str) -> int:
    """Return lower priority number for more actionable pytest artifacts."""

    return PYTEST_ARTIFACT_PRIORITY.get(Path(artifact_path).name, 10)


def resolved_artifact_path(log_dir: Path, artifact_path: str) -> Path:
    """Return artifact path from manifest path text."""

    path = Path(artifact_path)
    if path.is_absolute() or path.exists():
        return path
    return log_dir / path.name


def resolved_log_path(log_dir: Path, log_path: str) -> Path:
    """Return log path from manifest path text."""

    path = Path(log_path)
    if path.is_absolute() or path.exists():
        return path
    return log_dir / path.name


def generic_fact(record: FailureRecord) -> dict[str, object]:
    """Return generic fact when no structured artifact facts exist."""

    return fact_payload(
        {
            "check": record.name,
            "path": None,
            "line": None,
            "column": None,
            "symbol": None,
            "message": failure_message(record),
            "severity": "error",
        },
    )


def failure_message(record: FailureRecord) -> str:
    """Return exact message for one failed check record."""

    exit_text = "unknown" if record.exit_code is None else str(record.exit_code)
    return f"{record.name} failed with exit code {exit_text}"
