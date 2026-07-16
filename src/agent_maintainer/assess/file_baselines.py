"""Provider-neutral file assessment against defaults and per-path ceilings."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from agent_maintainer.assess import file_baseline_codec, file_baseline_state
from agent_maintainer.assess.models import (
    FileBaselineFinding,
    FileBaselineGroupSummary,
    FileBaselineReport,
)
from agent_maintainer.config.schema import FileBaselineGroupConfig, MaintainerConfig
from agent_maintainer.ecosystems.git_changes import FileChange, run_git_numstat

BRACE_OPEN = "{"
BRACE_CLOSE = "}"


class FileBaselineLifecycleError(ValueError):
    """One invalid or unsafe file ceiling baseline lifecycle request."""


def build_file_baseline_report(
    target: Path,
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
) -> FileBaselineReport:
    """Build a provider-neutral report against defaults and established ceilings."""
    if not config.file_baselines_enabled:
        return FileBaselineReport(
            target=str(target),
            enabled=False,
            mode=config.file_baselines_mode,
            groups=(),
            findings=(),
            next_commands=("Enable [tool.agent_maintainer.file_baselines] to assess file groups.",),
            passed=True,
        )
    observations = collect_observations(target, config.file_baselines)
    stored = _read_optional_baseline(target, config.file_baselines_baseline)
    comparison = file_baseline_state.compare_baseline(stored, observations)
    deltas = {(delta.group, delta.path): delta for delta in comparison.deltas}
    changes = _read_changes(base_ref, staged=staged)
    summaries: list[FileBaselineGroupSummary] = []
    findings: list[FileBaselineFinding] = []
    for group in config.file_baselines:
        group_observations = tuple(item for item in observations if item.group == group.name)
        group_changes = tuple(
            change for change in changes if _matches_group(Path(change.path), group)
        )
        group_findings = _group_findings(group, group_observations, group_changes, deltas)
        summaries.append(
            FileBaselineGroupSummary(
                name=group.name,
                role=group.role,
                matched_files=len(group_observations),
                changed_files=len(group_changes),
                changed_lines=sum(change.changed for change in group_changes),
                findings=len(group_findings),
            ),
        )
        findings.extend(group_findings)
    findings.extend(_removed_findings(comparison))
    return FileBaselineReport(
        target=str(target),
        enabled=True,
        mode=config.file_baselines_mode,
        groups=tuple(summaries),
        findings=tuple(findings),
        next_commands=_next_commands(findings),
        passed=comparison.passed,
    )


def _read_changes(base_ref: str, *, staged: bool) -> tuple[FileChange, ...]:
    """Return neutral Git changes or empty tuple outside Git comparisons."""
    try:
        return tuple(run_git_numstat(base_ref, staged=staged))
    except RuntimeError:
        return ()


def _matching_files(
    target: Path,
    group: FileBaselineGroupConfig,
) -> tuple[Path, ...]:
    """Return files matching include/exclude group patterns."""
    files: set[Path] = set()
    for pattern in _expanded_patterns(group.include):
        files.update(path for path in target.glob(pattern) if path.is_file())
    return tuple(
        sorted(
            (path for path in files if not _excluded(path.relative_to(target), group)),
            key=lambda path: path.as_posix(),
        ),
    )


def collect_observations(
    target: Path,
    groups: tuple[FileBaselineGroupConfig, ...],
) -> tuple[file_baseline_state.FileCeilingObservation, ...]:
    """Collect deterministic provider-neutral counts for configured group/path pairs."""
    observations: list[file_baseline_state.FileCeilingObservation] = []
    for group in groups:
        for path in _matching_files(target, group):
            physical, nonblank = _line_counts(path)
            observations.append(
                file_baseline_state.FileCeilingObservation(
                    group.name,
                    path.relative_to(target).as_posix(),
                    physical,
                    nonblank,
                    group.max_physical_lines,
                    group.max_nonblank_lines,
                )
            )
    return tuple(sorted(observations, key=lambda item: item.key))


def _group_findings(
    group: FileBaselineGroupConfig,
    observations: tuple[file_baseline_state.FileCeilingObservation, ...],
    changes: tuple[FileChange, ...],
    deltas: dict[tuple[str, str], file_baseline_state.FileCeilingDelta],
) -> tuple[FileBaselineFinding, ...]:
    """Return findings for one group."""
    findings: list[FileBaselineFinding] = []
    for observation in observations:
        delta = deltas.get(observation.key)
        if delta is not None:
            findings.extend(_ceiling_findings(group, delta))
    findings.extend(_change_findings(group, changes))
    return tuple(findings)


def _ceiling_findings(
    group: FileBaselineGroupConfig,
    delta: file_baseline_state.FileCeilingDelta,
) -> tuple[FileBaselineFinding, ...]:
    """Return regression or improvement findings for one observed path."""
    relative_path = Path(delta.path)
    findings: list[FileBaselineFinding] = []
    if delta.physical_regression:
        description = (
            f"{delta.physical} physical lines makes this a new oversized file; "
            f"default is {delta.physical_ceiling}"
            if delta.new_path
            else f"{delta.physical} physical lines exceeds baseline ceiling "
            f"{delta.physical_ceiling}"
        )
        findings.append(
            _finding(
                group,
                relative_path,
                "physical-lines",
                description,
                blocking=True,
            ),
        )
    if delta.nonblank_regression:
        description = (
            f"{delta.nonblank} nonblank lines makes this a new oversized file; "
            f"default is {delta.nonblank_ceiling}"
            if delta.new_path
            else f"{delta.nonblank} nonblank lines exceeds baseline ceiling "
            f"{delta.nonblank_ceiling}"
        )
        findings.append(
            _finding(
                group,
                relative_path,
                "nonblank-lines",
                description,
                blocking=True,
            ),
        )
    if delta.improved:
        findings.append(
            _finding(
                group,
                relative_path,
                "baseline-improvement",
                f"{delta.physical} physical/{delta.nonblank} nonblank lines improved "
                "and are eligible for prune",
            )
        )
    return tuple(findings)


def _removed_findings(
    comparison: file_baseline_state.FileCeilingComparison,
) -> tuple[FileBaselineFinding, ...]:
    """Return explicit prune suggestions for absent baseline paths."""
    return tuple(
        FileBaselineFinding(
            group=delta.group,
            path=delta.path,
            kind="baseline-removed",
            message="baseline path is absent and eligible for prune",
            recommendation=(
                "Review a rename as a new path, then prune the removed ceiling explicitly."
            ),
        )
        for delta in comparison.deltas
        if delta.removed
    )


def _change_findings(
    group: FileBaselineGroupConfig,
    changes: tuple[FileChange, ...],
) -> tuple[FileBaselineFinding, ...]:
    """Return changed-file and changed-line findings for one group."""
    findings: list[FileBaselineFinding] = []
    changed_lines = sum(change.changed for change in changes)
    if group.changed_file_warn and len(changes) > group.changed_file_warn:
        findings.append(
            _group_finding(
                group,
                "changed-files",
                f"{len(changes)} changed files exceeds {group.changed_file_warn}",
            ),
        )
    if group.changed_line_warn and changed_lines > group.changed_line_warn:
        findings.append(
            _group_finding(
                group,
                "changed-lines",
                f"{changed_lines} changed lines exceeds {group.changed_line_warn}",
            ),
        )
    return tuple(findings)


def _line_counts(path: Path) -> tuple[int, int]:
    """Return physical and nonblank line counts."""
    physical = 0
    nonblank = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        physical += 1
        if line.strip():
            nonblank += 1
    return physical, nonblank


def _finding(
    group: FileBaselineGroupConfig,
    path: Path,
    kind: str,
    message: str,
    *,
    blocking: bool = False,
) -> FileBaselineFinding:
    """Build one file-specific finding."""
    return FileBaselineFinding(
        group=group.name,
        path=path.as_posix(),
        kind=kind,
        message=message,
        recommendation=f"Inspect {path.as_posix()} or split the {group.role} surface.",
        blocking=blocking,
    )


def _group_finding(
    group: FileBaselineGroupConfig,
    kind: str,
    message: str,
) -> FileBaselineFinding:
    """Build one group-level finding."""
    return FileBaselineFinding(
        group=group.name,
        path="",
        kind=kind,
        message=message,
        recommendation=f"Split or explain the {group.name} change before promoting it.",
    )


def _next_commands(findings: list[FileBaselineFinding]) -> tuple[str, ...]:
    """Return compact follow-up commands."""
    if not findings:
        return ("python -m agent_maintainer assess file-baselines",)
    if any(finding.kind.startswith("baseline-") for finding in findings):
        return (
            "python -m agent_maintainer assess file-baselines prune --dry-run",
            "python -m agent_maintainer assess file-baselines --json",
        )
    return ("python -m agent_maintainer assess file-baselines --json",)


def _read_optional_baseline(
    target: Path,
    configured_path: str,
) -> file_baseline_state.FileCeilingBaseline | None:
    path = configured_baseline_path(target, configured_path)
    if not path.exists():
        return None
    try:
        return file_baseline_codec.read_baseline(path)
    except (OSError, ValueError) as exc:
        raise FileBaselineLifecycleError(f"invalid file ceiling baseline: {exc}") from exc


def configured_baseline_path(target: Path, configured_path: str) -> Path:
    candidate = (target / configured_path).resolve(strict=False)
    try:
        candidate.relative_to(target)
    except ValueError as exc:
        raise FileBaselineLifecycleError(
            "file ceiling baseline path escapes the target repository"
        ) from exc
    return candidate


def _matches_group(path: Path, group: FileBaselineGroupConfig) -> bool:
    """Return whether repo-relative path matches group include/exclude patterns."""
    normalized = path.as_posix()
    return any(
        _matches_pattern(normalized, pattern) for pattern in _expanded_patterns(group.include)
    ) and not _excluded(path, group)


def _excluded(path: Path, group: FileBaselineGroupConfig) -> bool:
    """Return whether repo-relative path is excluded by group patterns."""
    normalized = path.as_posix()
    return any(
        _matches_pattern(normalized, pattern) for pattern in _expanded_patterns(group.exclude)
    )


def _matches_pattern(path: str, pattern: str) -> bool:
    """Return whether path matches a glob pattern including direct `**` files."""
    if fnmatch(path, pattern):
        return True
    if "/**/" in pattern:
        return fnmatch(path, pattern.replace("/**/", "/"))
    return False


def _expanded_patterns(patterns: tuple[str, ...]) -> tuple[str, ...]:
    """Expand one-level brace glob syntax for convenience."""
    expanded: list[str] = []
    for pattern in patterns:
        expanded.extend(_expand_braces(pattern))
    return tuple(expanded)


def _expand_braces(pattern: str) -> tuple[str, ...]:
    """Expand simple glob braces such as `*.{ts,tsx}`."""
    start = pattern.find(BRACE_OPEN)
    end = pattern.find(BRACE_CLOSE, start + 1)
    if start < 0 or end < 0:
        return (pattern,)
    prefix = pattern[:start]
    suffix = pattern[end + 1 :]
    options = tuple(option.strip() for option in pattern[start + 1 : end].split(","))
    return tuple(f"{prefix}{option}{suffix}" for option in options if option)
