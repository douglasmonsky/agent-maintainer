"""Collect current findings for ratchet baselines."""

from __future__ import annotations

import hashlib
from pathlib import Path

from agent_maintainer.checks import file_lengths, structure
from agent_maintainer.config.schema import FRESH_STRICT_MODE
from agent_maintainer.core.config import MaintainerConfig, load_config
from agent_maintainer.ratchet.models import RatchetFinding

FILE_LENGTH_CHECK = "file-length"
STRUCTURE_CHECK = "structure-cohesion"
DEFAULT_CHECKS = (FILE_LENGTH_CHECK, STRUCTURE_CHECK)
FINGERPRINT_LENGTH = 20


def current_findings(
    checks: tuple[str, ...] = DEFAULT_CHECKS,
    config: MaintainerConfig | None = None,
) -> tuple[RatchetFinding, ...]:
    """Return current findings for selected ratchet checks."""

    active_config = config or load_config()
    collected: list[RatchetFinding] = []
    if FILE_LENGTH_CHECK in checks:
        collected.extend(file_length_findings(active_config))
    if STRUCTURE_CHECK in checks:
        collected.extend(structure_findings(active_config))
    return tuple(sorted(collected, key=lambda finding: finding.fingerprint))


def file_length_findings(config: MaintainerConfig) -> tuple[RatchetFinding, ...]:
    """Return oversized Python-file findings."""

    expanded = file_lengths.expand_paths([], changed_only=False)
    eligible = file_lengths.eligible_python_paths(expanded, include_generated=False)
    findings: list[RatchetFinding] = []
    for path in eligible:
        physical, source = file_lengths.count_lines(path)
        findings.extend(
            metric_findings(
                path,
                (("physical-lines", physical, config.file_length_max_physical),),
            ),
        )
        findings.extend(
            metric_findings(
                path,
                (("source-lines", source, config.file_length_max_source),),
            ),
        )
    return tuple(findings)


def structure_findings(config: MaintainerConfig) -> tuple[RatchetFinding, ...]:
    """Return folder-structure cohesion findings."""

    block_threshold = configured_structure_block_threshold(config)
    raw_findings = structure.structure_findings(
        structure.python_files(config.structure_paths, config.structure_ignore_paths),
        warn_threshold=config.folder_file_warn,
        block_threshold=block_threshold,
        patterns=config.structure_hint_patterns,
        cluster_min=config.structure_cluster_min,
    )
    return tuple(structure_finding(raw, block_threshold, config) for raw in raw_findings)


def metric_findings(
    path: Path,
    metrics: tuple[tuple[str, int, int], ...],
) -> tuple[RatchetFinding, ...]:
    """Return file-length findings for exceeded metrics."""

    repo_path = file_lengths.baseline_key(path)
    return tuple(
        RatchetFinding(
            check=FILE_LENGTH_CHECK,
            identity=f"{repo_path}:{metric}",
            path=repo_path,
            line=None,
            severity="fail",
            metric=metric,
            value=value,
            threshold=threshold,
            message=f"{repo_path} has {value} {metric}; threshold is {threshold}.",
            fingerprint=fingerprint(FILE_LENGTH_CHECK, f"{repo_path}:{metric}"),
        )
        for metric, value, threshold in metrics
        if value > threshold
    )


def structure_finding(
    finding: structure.FolderFinding,
    block_threshold: int,
    config: MaintainerConfig,
) -> RatchetFinding:
    """Normalize one structure-cohesion finding."""

    path = file_lengths.baseline_key(finding.folder)
    threshold = block_threshold if finding.severity == structure.FAIL else config.folder_file_warn
    return RatchetFinding(
        check=STRUCTURE_CHECK,
        identity=path,
        path=path,
        line=None,
        severity=finding.severity.lower(),
        metric="python-files",
        value=finding.count,
        threshold=threshold,
        message=structure_message(finding, threshold),
        fingerprint=fingerprint(STRUCTURE_CHECK, path),
    )


def configured_structure_block_threshold(config: MaintainerConfig) -> int:
    """Return active structure block threshold."""

    if config.mode == FRESH_STRICT_MODE:
        return config.folder_file_block
    return 0


def structure_message(finding: structure.FolderFinding, threshold: int) -> str:
    """Return compact structure finding message."""

    return (
        f"{file_lengths.baseline_key(finding.folder)} has {finding.count} Python "
        f"files; threshold is {threshold}."
    )


def fingerprint(check: str, identity: str) -> str:
    """Return a stable non-secret finding fingerprint."""

    payload = f"{check}\0{identity}".encode()
    return hashlib.sha256(payload).hexdigest()[:FINGERPRINT_LENGTH]
