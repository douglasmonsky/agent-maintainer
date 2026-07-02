"""Check folder-level Python structure cohesion signals."""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import FRESH_STRICT_MODE
from agent_maintainer.core.config import MaintainerConfig, load_config
from agent_maintainer.ecosystems.python.classification import is_python_path

FAIL = "FAIL"
WARN = "WARN"
HINT_PREVIEW_LIMIT = 4
LAYER_WORDS = frozenset(
    (
        "args",
        "checks",
        "cli",
        "config",
        "doctor",
        "executor",
        "models",
        "reporting",
    )
)


@dataclass(frozen=True)
class FolderFinding:
    """One folder-level structure finding."""

    folder: Path
    count: int
    severity: str
    hints: tuple[str, ...]


@dataclass(frozen=True)
class StructurePolicy:
    """Thresholds and hint configuration for structure checks."""

    warn_threshold: int
    block_threshold: int
    patterns: tuple[str, ...]
    cluster_min: int


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse structure checker arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--warn-threshold", type=int)
    parser.add_argument("--block-threshold", type=int)
    parser.add_argument("--ignore", action="append", default=[])
    parser.add_argument("--hint-pattern", action="append", default=[])
    parser.add_argument("--cluster-min", type=int)
    return parser.parse_args(argv)


def selected_paths(args: argparse.Namespace, config: MaintainerConfig) -> tuple[str, ...]:
    """Return paths checked for structure signals."""

    if args.paths:
        return tuple(args.paths)
    if config.structure_paths:
        return config.structure_paths
    return config.source_roots


def selected_block_threshold(args: argparse.Namespace, config: MaintainerConfig) -> int:
    """Return active block threshold, fresh-strict only by default."""

    if args.block_threshold is not None:
        return args.block_threshold
    if config.mode == FRESH_STRICT_MODE:
        return config.folder_file_block
    return 0


def relative_path(path: Path) -> str:
    """Return stable repository-relative path string."""

    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def ignored(path: Path, patterns: tuple[str, ...]) -> bool:
    """Return whether path matches an ignored glob pattern."""

    relative = relative_path(path)
    return any(
        fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern)
        for pattern in patterns
    )


def python_files(paths: tuple[str, ...], ignored_patterns: tuple[str, ...]) -> list[Path]:
    """Return Python files under configured paths excluding ignored globs."""

    files: list[Path] = []
    for path_text in paths:
        root = Path(path_text)
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else root.rglob("*.py")
        files.extend(
            path
            for path in candidates
            if path.is_file() and is_python_path(path) and not ignored(path, ignored_patterns)
        )
    return sorted(set(files))


def files_by_folder(files: list[Path]) -> dict[Path, list[Path]]:
    """Group files by parent folder."""

    grouped: dict[Path, list[Path]] = defaultdict(list)
    for path in files:
        grouped[path.parent].append(path)
    return dict(grouped)


def regex_hints(files: list[Path], patterns: tuple[str, ...], cluster_min: int) -> list[str]:
    """Return regex-based cluster hints for one folder."""

    stems = [path.stem for path in files]
    hints: list[str] = []
    for pattern in patterns:
        regex = re.compile(pattern)
        matched = [stem for stem in stems if regex.search(stem)]
        if len(matched) >= cluster_min:
            hints.append(cluster_message(f"pattern {pattern!r}", matched))
    return hints


def layer_mix_hints(files: list[Path], cluster_min: int) -> list[str]:
    """Return layer-mixing hints for one folder."""

    stems = [path.stem for path in files]
    matched = [
        stem
        for stem in stems
        if any(word in stem.split("_") or stem == word for word in LAYER_WORDS)
    ]
    if len(matched) < cluster_min:
        return []
    return [cluster_message("layer words", matched)]


def cluster_message(label: str, stems: list[str]) -> str:
    """Return compact cluster hint message."""

    preview = ", ".join(sorted(stems)[:HINT_PREVIEW_LIMIT])
    remainder = len(stems) - HINT_PREVIEW_LIMIT
    suffix = f", +{remainder} more" if remainder > 0 else ""
    return f"{label} matched {len(stems)} files ({preview}{suffix})"


def folder_finding(
    folder: Path,
    files: list[Path],
    policy: StructurePolicy,
) -> FolderFinding | None:
    """Return finding for one folder when thresholds are met."""

    count = len(files)
    severity = ""
    if policy.block_threshold > 0 and count >= policy.block_threshold:
        severity = FAIL
    elif count >= policy.warn_threshold:
        severity = WARN
    if not severity:
        return None
    hints = (
        *regex_hints(files, policy.patterns, policy.cluster_min),
        *layer_mix_hints(files, policy.cluster_min),
    )
    return FolderFinding(folder, count, severity, hints)


def structure_findings(
    files: list[Path],
    *,
    warn_threshold: int,
    block_threshold: int,
    patterns: tuple[str, ...],
    cluster_min: int,
) -> list[FolderFinding]:
    """Return folder count findings for all grouped files."""

    policy = StructurePolicy(
        warn_threshold=warn_threshold,
        block_threshold=block_threshold,
        patterns=patterns,
        cluster_min=cluster_min,
    )
    return [
        finding
        for folder, grouped_files in sorted(files_by_folder(files).items())
        if (
            finding := folder_finding(
                folder,
                grouped_files,
                policy,
            )
        )
    ]


def print_finding(finding: FolderFinding, warn_threshold: int, block_threshold: int) -> None:
    """Print one structure finding."""

    threshold = block_threshold if finding.severity == FAIL else warn_threshold
    print(
        f"{finding.severity}: Folder {relative_path(finding.folder)!r} has "
        f"{finding.count} Python files (threshold: {threshold}). "
        "Consider splitting by responsibility if these files form multiple concepts."
    )
    for hint in finding.hints:
        print(f"  hint: {hint}")


def main(argv: list[str] | None = None) -> int:
    """Run structure cohesion check."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_config()
    paths = selected_paths(args, config)
    ignored_patterns = tuple(args.ignore) or config.structure_ignore_paths
    hint_patterns = tuple(args.hint_pattern) or config.structure_hint_patterns
    warn_threshold = config.folder_file_warn if args.warn_threshold is None else args.warn_threshold
    block_threshold = selected_block_threshold(args, config)
    cluster_min = config.structure_cluster_min if args.cluster_min is None else args.cluster_min
    findings = structure_findings(
        python_files(paths, ignored_patterns),
        warn_threshold=warn_threshold,
        block_threshold=block_threshold,
        patterns=hint_patterns,
        cluster_min=cluster_min,
    )
    for structure_finding in findings:
        print_finding(structure_finding, warn_threshold, block_threshold)
    return 1 if any(result.severity == FAIL for result in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
