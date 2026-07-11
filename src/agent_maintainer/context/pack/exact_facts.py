"""Extract exact repair facts from verifier artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from agent_context.failures import FailureRecord
from agent_context.reading import file_safety
from agent_repair_facts import registry as fact_parsers
from agent_repair_facts.payloads import fact_payload

MAX_FACTS_PER_CHECK = 5
MAX_EXACT_FACT_INPUT_BYTES = 8_388_608
MAX_EXACT_FACT_TOTAL_BYTES = 16_777_216
MAX_EXACT_FACT_FILES = 32
PYTEST_ARTIFACT_PRIORITY = MappingProxyType(
    {
        "pytest-junit.xml": 0,
        "coverage.json": 1,
    },
)


def _empty_seen_paths() -> set[Path]:
    return set()


@dataclass
class ExactFactReadBudget:
    """Aggregate exact-fact parser budget for one context pack."""

    remaining_bytes: int = MAX_EXACT_FACT_TOTAL_BYTES
    remaining_files: int = MAX_EXACT_FACT_FILES
    seen_paths: set[Path] = field(default_factory=_empty_seen_paths)

    def read_text(self, path: Path) -> str | None:
        """Read and charge one unique path through the bounded safe reader."""

        if self.remaining_files <= 0 or self.remaining_bytes <= 0:
            return None
        canonical = _canonical_path(path)
        if canonical is None or canonical in self.seen_paths:
            return None
        self.seen_paths.add(canonical)
        self.remaining_files -= 1
        safe_read = file_safety.read_bounded_utf8_file(
            path,
            max_bytes=min(MAX_EXACT_FACT_INPUT_BYTES, self.remaining_bytes),
        )
        if safe_read.text is None:
            return None
        actual_bytes = len(safe_read.text.encode("utf-8"))
        if actual_bytes > self.remaining_bytes:
            return None
        self.remaining_bytes -= actual_bytes
        return safe_read.text


def repair_facts(
    log_dir: Path,
    records: tuple[FailureRecord, ...],
    *,
    workspace_root: Path | None = None,
    require_relative_paths: bool = False,
    read_budget: ExactFactReadBudget | None = None,
) -> list[dict[str, object]]:
    """Return bounded exact repair facts for failed checks."""

    facts: list[dict[str, object]] = []
    budget = read_budget or ExactFactReadBudget()
    for record in records:
        extracted = structured_facts(
            log_dir,
            record,
            workspace_root=workspace_root,
            require_relative_paths=require_relative_paths,
            read_budget=budget,
        )
        facts.extend(extracted[:MAX_FACTS_PER_CHECK] or [generic_fact(record)])
    return facts


def structured_facts(
    log_dir: Path,
    record: FailureRecord,
    *,
    workspace_root: Path | None = None,
    require_relative_paths: bool = False,
    read_budget: ExactFactReadBudget | None = None,
) -> list[dict[str, object]]:
    """Return facts extracted from known artifacts and logs."""

    artifact_facts: list[dict[str, object]] = []
    budget = read_budget or ExactFactReadBudget()
    for artifact_path in artifact_paths_for(record):
        resolved = resolved_artifact_path(
            log_dir,
            artifact_path,
            workspace_root=workspace_root,
            require_relative_paths=require_relative_paths,
        )
        if resolved is not None:
            parsed = _artifact_facts(record.name, resolved, budget)
            artifact_facts.extend(parsed[: MAX_FACTS_PER_CHECK - len(artifact_facts)])
        if len(artifact_facts) >= MAX_FACTS_PER_CHECK:
            break
    if artifact_facts:
        return artifact_facts
    resolved_log = resolved_log_path(
        log_dir,
        record.log_path,
        workspace_root=workspace_root,
        require_relative_paths=require_relative_paths,
    )
    if resolved_log is None:
        return []
    log_text = budget.read_text(resolved_log)
    if log_text is None:
        return []
    return fact_parsers.log_facts_from_text(
        record.name,
        resolved_log,
        log_text,
    )[:MAX_FACTS_PER_CHECK]


def _artifact_facts(
    check: str,
    path: Path,
    budget: ExactFactReadBudget,
) -> list[dict[str, object]]:
    """Return artifact facts from one bounded, already-read source."""

    artifact_text = budget.read_text(path)
    if artifact_text is None:
        return []
    return fact_parsers.artifact_facts_from_text(check, path, artifact_text)


def artifact_paths_for(record: FailureRecord) -> tuple[str, ...]:
    """Return artifact paths ordered by usefulness for exact facts."""

    if record.name != "pytest-coverage":
        return record.artifact_paths
    return tuple(sorted(record.artifact_paths, key=pytest_artifact_priority))


def pytest_artifact_priority(artifact_path: str) -> int:
    """Return lower priority number for more actionable pytest artifacts."""

    return PYTEST_ARTIFACT_PRIORITY.get(Path(artifact_path).name, 10)


def resolved_artifact_path(
    log_dir: Path,
    artifact_path: str,
    *,
    workspace_root: Path | None = None,
    require_relative_paths: bool = False,
) -> Path | None:
    """Return artifact path from manifest path text."""

    path = Path(artifact_path)
    if require_relative_paths:
        return _resolved_confined_path(
            log_dir,
            path,
            workspace_root=workspace_root,
        )
    if path.is_absolute() or path.exists():
        return path
    return log_dir / path.name


def resolved_log_path(
    log_dir: Path,
    log_path: str,
    *,
    workspace_root: Path | None = None,
    require_relative_paths: bool = False,
) -> Path | None:
    """Return log path from manifest path text."""

    path = Path(log_path)
    if require_relative_paths:
        return _resolved_confined_path(
            log_dir,
            path,
            workspace_root=workspace_root,
        )
    if path.is_absolute() or path.exists():
        return path
    return log_dir / path.name


def _resolved_confined_path(
    log_dir: Path,
    path: Path,
    *,
    workspace_root: Path | None,
) -> Path | None:
    """Resolve one manifest path to the exact safe path a parser may open."""

    if _unsafe_manifest_path(path):
        return None
    root = (Path.cwd() if workspace_root is None else workspace_root).resolve()
    resolved_log_dir = log_dir if log_dir.is_absolute() else root / log_dir
    rooted = root / path
    candidate = rooted if rooted.exists() else resolved_log_dir / path.name
    confined = file_safety.confined_path(candidate, workspace_root=root)
    if isinstance(confined, file_safety.FileSafety):
        return None
    refusal = file_safety.inspect_path(confined, max_bytes=MAX_EXACT_FACT_INPUT_BYTES)
    if refusal is None:
        return confined
    return None


def _unsafe_manifest_path(path: Path) -> bool:
    """Return whether manifest path text is unsafe to resolve."""

    return (
        len(path.parts) == 0
        or path.is_absolute()
        or ".." in path.parts
        or file_safety.sensitive_path(path)
    )


def _canonical_path(path: Path) -> Path | None:
    """Return a canonical identity for deduplicating read attempts."""

    try:
        return path.resolve(strict=True)
    except OSError:
        return None


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
