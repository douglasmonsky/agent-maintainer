"""Advisory TypeScript LCOV coverage for executable changed lines."""

from __future__ import annotations

import re
import subprocess  # nosec B404
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.ecosystems.models import FileRole
from agent_maintainer.ecosystems.typescript.classification import classify_path
from agent_maintainer.test_intel import coverage_lines
from agent_repair_facts.parsers.typescript_coverage import (
    LcovFileRecord,
    parse_lcov_records,
)

DEFAULT_LCOV_PATH = Path("coverage/lcov.info")
MAX_LCOV_BYTES = 10 * 1024 * 1024
MAX_SOURCE_PATH_CHARS = 500
MAX_FILE_FACTS = 500
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:/")
GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40,64}$")
ADVISORY_NOTE = (
    "Advisory only: missing LCOV files are reported separately and no "
    "coverage threshold is enforced."
)


class TypeScriptCoverageError(RuntimeError):
    """User-actionable TypeScript coverage report failure."""


@dataclass(frozen=True)
class TypeScriptCoverageRequest:
    """Inputs for one advisory TypeScript coverage report."""

    repo_root: Path
    lcov_path: Path = DEFAULT_LCOV_PATH
    source_root: Path = Path(".")
    base_ref: str = "HEAD"
    staged: bool = False


@dataclass(frozen=True)
class TypeScriptCoverageFileFact:
    """Changed-line coverage counts for one LCOV-matched source file."""

    path: str
    executable_changed_lines: int
    covered_changed_lines: int
    missed_changed_lines: int
    changed_line_coverage: float | None

    def to_json(self) -> dict[str, object]:
        """Return a stable JSON payload."""

        return {
            "path": self.path,
            "executable_changed_lines": self.executable_changed_lines,
            "covered_changed_lines": self.covered_changed_lines,
            "missed_changed_lines": self.missed_changed_lines,
            "changed_line_coverage": self.changed_line_coverage,
        }


@dataclass(frozen=True)
class TypeScriptCoverageReport:
    """Bounded advisory TypeScript changed-line coverage report."""

    artifact_path: str
    source_root: str
    base_ref: str
    staged: bool
    changed_source: tuple[str, ...]
    missing_from_lcov: tuple[str, ...]
    executable_changed_lines: int
    covered_changed_lines: int
    missed_changed_lines: int
    changed_line_coverage: float | None
    matched_file_count: int
    files: tuple[TypeScriptCoverageFileFact, ...]
    note: str = ADVISORY_NOTE

    def to_json(self) -> dict[str, object]:
        """Return a stable JSON payload."""

        return {
            "artifact_path": self.artifact_path,
            "source_root": self.source_root,
            "base_ref": self.base_ref,
            "staged": self.staged,
            "changed_source": list(self.changed_source),
            "missing_from_lcov": list(self.missing_from_lcov),
            "executable_changed_lines": self.executable_changed_lines,
            "covered_changed_lines": self.covered_changed_lines,
            "missed_changed_lines": self.missed_changed_lines,
            "changed_line_coverage": self.changed_line_coverage,
            "matched_file_count": self.matched_file_count,
            "files": [fact.to_json() for fact in self.files],
            "note": self.note,
        }


@dataclass
class _MutableLineRecord:
    """Merged LCOV line sets during repository path normalization."""

    executable: set[int]
    covered: set[int]


class _GitDiff:
    """Strict Git boundary for advisory changed-line reporting."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def resolve_ref(self, *, base_ref: str, staged: bool) -> str:
        """Resolve one base ref to a canonical object ID before diffing."""

        if staged:
            return base_ref
        command = ["git", "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}"]
        try:
            result = subprocess.run(  # nosec B603
                command,
                cwd=self._repo_root,
                capture_output=True,
                check=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
            raise TypeScriptCoverageError("Git ref could not be resolved.") from exc
        object_id = result.stdout.strip()
        if GIT_OBJECT_RE.fullmatch(object_id) is None:
            raise TypeScriptCoverageError("Git ref could not be resolved.")
        return object_id

    def changed_line_numbers(
        self,
        changed_source: tuple[str, ...],
        *,
        base_ref: str,
        staged: bool,
    ) -> dict[str, frozenset[int]]:
        """Map changed lines while surfacing Git and decoding failures."""

        command = coverage_lines.git_diff_command(
            changed_source,
            base_ref=base_ref,
            staged=staged,
        )
        try:
            result = subprocess.run(  # nosec B603
                command,
                cwd=self._repo_root,
                capture_output=True,
                check=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
            raise TypeScriptCoverageError("Git diff could not map changed lines.") from exc
        return coverage_lines.parse_changed_lines(result.stdout, frozenset(changed_source))


def build_report(request: TypeScriptCoverageRequest) -> TypeScriptCoverageReport:
    """Build an advisory TypeScript changed-line coverage report."""

    repo_root = request.repo_root.resolve()
    if not repo_root.is_dir():
        raise TypeScriptCoverageError("Repository root is not a directory.")
    artifact = confined_path(repo_root, request.lcov_path, "LCOV artifact")
    source_root = confined_path(repo_root, request.source_root, "Source root")
    if not source_root.is_dir():
        raise TypeScriptCoverageError("Source root is not a directory.")

    raw_output = read_lcov_artifact(artifact)
    records = normalize_records(
        parse_lcov_records(raw_output),
        repo_root=repo_root,
        source_root=source_root,
    )
    if not any(record.executable for record in records.values()):
        raise TypeScriptCoverageError("Artifact contains no usable LCOV line records.")

    diff_ref = _GitDiff(repo_root).resolve_ref(
        base_ref=request.base_ref,
        staged=request.staged,
    )
    changed_source = changed_typescript_source_paths(
        repo_root,
        base_ref=diff_ref,
        staged=request.staged,
    )
    changed_map = _GitDiff(repo_root).changed_line_numbers(
        changed_source,
        base_ref=diff_ref,
        staged=request.staged,
    )
    facts, missing = coverage_facts(changed_source, changed_map, records)
    executable = sum(fact.executable_changed_lines for fact in facts)
    covered = sum(fact.covered_changed_lines for fact in facts)
    return TypeScriptCoverageReport(
        artifact_path=relative_label(artifact, repo_root),
        source_root=relative_label(source_root, repo_root),
        base_ref=request.base_ref,
        staged=request.staged,
        changed_source=changed_source,
        missing_from_lcov=missing,
        executable_changed_lines=executable,
        covered_changed_lines=covered,
        missed_changed_lines=executable - covered,
        changed_line_coverage=coverage_percent(covered, executable),
        matched_file_count=len(facts),
        files=facts[:MAX_FILE_FACTS],
    )


def confined_path(repo_root: Path, path: Path, label: str) -> Path:
    """Resolve one input and require it to remain inside the repository."""

    candidate = path if path.is_absolute() else repo_root / path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo_root):
        raise TypeScriptCoverageError(f"{label} must stay inside the repository.")
    return resolved


def read_lcov_artifact(path: Path) -> str:
    """Read one regular, bounded UTF-8 LCOV artifact."""

    try:
        raw = read_lcov_bytes(path)
    except OSError as exc:
        raise TypeScriptCoverageError("LCOV artifact could not be read.") from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TypeScriptCoverageError("LCOV artifact is not valid UTF-8.") from exc


def read_lcov_bytes(path: Path) -> bytes:
    """Return bounded bytes from one regular LCOV artifact."""

    metadata = path.stat()
    if not path.is_file():
        raise TypeScriptCoverageError("LCOV artifact is not a regular file.")
    require_lcov_size(metadata.st_size)
    with path.open("rb") as handle:
        raw = handle.read(MAX_LCOV_BYTES + 1)
    require_lcov_size(len(raw))
    return raw


def require_lcov_size(size: int) -> None:
    """Reject LCOV content larger than the explicit artifact bound."""

    if size > MAX_LCOV_BYTES:
        raise TypeScriptCoverageError("LCOV artifact exceeds the 10 MiB limit.")


def normalize_records(
    records: tuple[LcovFileRecord, ...],
    *,
    repo_root: Path,
    source_root: Path,
) -> dict[str, _MutableLineRecord]:
    """Return LCOV records merged by safe repository-relative path."""

    merged: dict[str, _MutableLineRecord] = {}
    for record in records:
        path = normalize_source_path(record.source, repo_root, source_root)
        if path is None:
            continue
        target = merged.setdefault(path, _MutableLineRecord(set(), set()))
        target.executable.update(record.executable_lines)
        target.covered.update(record.covered_lines)
    return dict(sorted(merged.items()))


def normalize_source_path(source: str, repo_root: Path, source_root: Path) -> str | None:
    """Return one safe repository-relative LCOV source path."""

    normalized = source.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if unsafe_source_scalar(normalized):
        return None
    candidate = Path(normalized) if normalized.startswith("/") else source_root / normalized
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.is_relative_to(repo_root):
        return None
    relative = resolved.relative_to(repo_root).as_posix()
    if relative == "." or len(relative) > MAX_SOURCE_PATH_CHARS:
        return None
    return relative


def unsafe_source_scalar(source: str) -> bool:
    """Return whether an LCOV source scalar is unsafe to resolve."""

    unsafe_shape = any(
        (
            not source,
            source == ".",
            len(source) > MAX_SOURCE_PATH_CHARS,
            source.startswith("//"),
            WINDOWS_DRIVE_RE.match(source) is not None,
        )
    )
    return unsafe_shape or has_unicode_control(source)


def has_unicode_control(value: str) -> bool:
    """Return whether text contains any Unicode control or format scalar."""

    return any(unicodedata.category(character).startswith("C") for character in value)


def changed_typescript_source_paths(
    repo_root: Path,
    *,
    base_ref: str,
    staged: bool,
) -> tuple[str, ...]:
    """Return changed non-deleted TypeScript/JavaScript source paths."""

    command = [
        "git",
        "diff",
        "--name-only",
        "-z",
        "-C",
        "--find-copies-harder",
        "--diff-filter=ACMR",
    ]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    try:
        result = subprocess.run(  # nosec B603
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise TypeScriptCoverageError("Git diff could not identify changed source.") from exc
    return tuple(
        path for path in sorted(set(result.stdout.split("\0")) - {""}) if is_typescript_source(path)
    )


def is_typescript_source(path: str) -> bool:
    """Return whether a path is provider-classified source."""

    if unsafe_source_scalar(path.replace("\\", "/")):
        return False
    classification = classify_path(path)
    return classification is not None and classification.role is FileRole.SOURCE


def coverage_facts(
    changed_source: tuple[str, ...],
    changed_map: dict[str, frozenset[int]],
    records: dict[str, _MutableLineRecord],
) -> tuple[tuple[TypeScriptCoverageFileFact, ...], tuple[str, ...]]:
    """Return per-file coverage facts and paths absent from LCOV."""

    facts: list[TypeScriptCoverageFileFact] = []
    missing: list[str] = []
    for path in changed_source:
        record = records.get(path)
        if record is None:
            missing.append(path)
            continue
        executable_lines = set(changed_map.get(path, frozenset())) & record.executable
        covered_lines = executable_lines & record.covered
        executable = len(executable_lines)
        covered = len(covered_lines)
        facts.append(
            TypeScriptCoverageFileFact(
                path=path,
                executable_changed_lines=executable,
                covered_changed_lines=covered,
                missed_changed_lines=executable - covered,
                changed_line_coverage=coverage_percent(covered, executable),
            )
        )
    return tuple(facts), tuple(missing)


def coverage_percent(covered: int, executable: int) -> float | None:
    """Return a rounded percentage for a non-empty executable denominator."""

    if executable == 0:
        return None
    return round(covered / executable * coverage_lines.PERCENT_SCALE, 2)


def relative_label(path: Path, repo_root: Path) -> str:
    """Return one repository-relative display label."""

    relative = path.relative_to(repo_root).as_posix()
    return relative or "."
