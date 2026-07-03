"""Provider-neutral advisory file baseline assessment."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from agent_maintainer.assess.models import (
    FileBaselineFinding,
    FileBaselineGroupSummary,
    FileBaselineReport,
)
from agent_maintainer.config.schema import FileBaselineGroupConfig, MaintainerConfig
from agent_maintainer.ecosystems.git_changes import FileChange, run_git_numstat

BRACE_OPEN = "{"
BRACE_CLOSE = "}"


def build_file_baseline_report(
    target: Path,
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
) -> FileBaselineReport:
    """Build advisory file baseline report for configured groups."""
    if not config.file_baselines_enabled:
        return FileBaselineReport(
            target=str(target),
            enabled=False,
            mode=config.file_baselines_mode,
            groups=(),
            findings=(),
            next_commands=("Enable [tool.agent_maintainer.file_baselines] to assess file groups.",),
        )
    changes = _read_changes(base_ref, staged=staged)
    summaries: list[FileBaselineGroupSummary] = []
    findings: list[FileBaselineFinding] = []
    for group in config.file_baselines:
        group_files = tuple(_matching_files(target, group))
        group_changes = tuple(
            change for change in changes if _matches_group(Path(change.path), group)
        )
        group_findings = _group_findings(group, group_files, group_changes, target)
        summaries.append(
            FileBaselineGroupSummary(
                name=group.name,
                role=group.role,
                matched_files=len(group_files),
                changed_files=len(group_changes),
                changed_lines=sum(change.changed for change in group_changes),
                findings=len(group_findings),
            ),
        )
        findings.extend(group_findings)
    return FileBaselineReport(
        target=str(target),
        enabled=True,
        mode=config.file_baselines_mode,
        groups=tuple(summaries),
        findings=tuple(findings),
        next_commands=_next_commands(findings),
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


def _group_findings(
    group: FileBaselineGroupConfig,
    files: tuple[Path, ...],
    changes: tuple[FileChange, ...],
    target: Path,
) -> tuple[FileBaselineFinding, ...]:
    """Return findings for one group."""
    findings: list[FileBaselineFinding] = []
    for path in files:
        findings.extend(_line_findings(group, path, target))
    findings.extend(_change_findings(group, changes))
    return tuple(findings)


def _line_findings(
    group: FileBaselineGroupConfig,
    path: Path,
    target: Path,
) -> tuple[FileBaselineFinding, ...]:
    """Return line-count findings for one file."""
    physical, nonblank = _line_counts(path)
    relative_path = path.relative_to(target)
    findings: list[FileBaselineFinding] = []
    if group.max_physical_lines and physical > group.max_physical_lines:
        findings.append(
            _finding(
                group,
                relative_path,
                "physical-lines",
                f"{physical} physical lines exceeds {group.max_physical_lines}",
            ),
        )
    if group.max_nonblank_lines and nonblank > group.max_nonblank_lines:
        findings.append(
            _finding(
                group,
                relative_path,
                "nonblank-lines",
                f"{nonblank} nonblank lines exceeds {group.max_nonblank_lines}",
            ),
        )
    return tuple(findings)


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
) -> FileBaselineFinding:
    """Build one file-specific finding."""
    return FileBaselineFinding(
        group=group.name,
        path=path.as_posix(),
        kind=kind,
        message=message,
        recommendation=f"Inspect {path.as_posix()} or split the {group.role} surface.",
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
    return ("python -m agent_maintainer assess file-baselines --json",)


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
