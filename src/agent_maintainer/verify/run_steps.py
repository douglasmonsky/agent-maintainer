"""Verifier run steps shared by quiet CLI orchestration."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, Protocol

from agent_maintainer.core.check_run import utc_timestamp
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.core.executor import run_check
from agent_maintainer.core.layout import layout_failures
from agent_maintainer.models import CI_PROFILE, Check, CheckResult
from agent_maintainer.verify.artifacts import RunContext, write_run_artifacts
from agent_maintainer.verify.git_refs import ref_failures


class CheckRuntimeEvents(Protocol):
    """Check-level runtime event reporter used by verifier steps."""

    def selected(self, checks: Sequence[Check]) -> None:
        """Record selected checks."""

    def check_started(self, check: Check) -> None:
        """Record check start."""

    def check_finished(self, result: CheckResult) -> None:
        """Record check finish."""

    def check_exception(self, check: Check, exc: Exception) -> None:
        """Record check exception."""


class ArtifactRuntimeEvents(Protocol):
    """Artifact runtime event reporter used by verifier steps."""

    def artifact_written(self, *, path: str, kind: str) -> None:
        """Record artifact write."""

    def artifact_removed(self, *, path: str, kind: str) -> None:
        """Record artifact removal."""

    def artifact_retention_pruned(
        self,
        *,
        log_dir: Path,
        pruned_count: int,
        keep: int,
    ) -> None:
        """Record run artifact retention pruning."""


class ArtifactWriteOptions(NamedTuple):
    """Options for writing verifier artifacts."""

    run_id: str
    runtime_events: ArtifactRuntimeEvents | None = None


def log_dir_for(config: MaintainerConfig) -> Path:
    """Return configured verifier log artifact directory."""

    return Path(config.diagnostic_artifacts_dir)


def emit_layout_failure(failures: list[str], log_dir: Path) -> CheckResult:
    """Write and return synthetic failure for invalid maintainer layout."""

    timestamp = utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    failure_lines = "\n".join(f"  {failure}" for failure in failures)
    output = f"Maintainer layout/configuration failed:\n\n{failure_lines}"
    log_path = log_dir / "maintainer-layout.log"
    log_path.write_text(f"{output}\n", encoding="utf-8")
    return CheckResult(
        "maintainer-layout",
        passed=False,
        output=output,
        log_path=str(log_path),
        started_at=timestamp,
        ended_at=timestamp,
    )


def emit_ref_failure(failures: list[str], log_dir: Path) -> CheckResult:
    """Write and return synthetic failure for invalid Git refs."""

    timestamp = utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    failure_lines = "\n".join(f"  {failure}" for failure in failures)
    output = f"Git reference validation failed:\n\n{failure_lines}"
    log_path = log_dir / "git-ref-validation.log"
    log_path.write_text(f"{output}\n", encoding="utf-8")
    return CheckResult(
        "git-ref-validation",
        passed=False,
        output=output,
        log_path=str(log_path),
        started_at=timestamp,
        ended_at=timestamp,
    )


def collect_results(
    args: argparse.Namespace,
    config: MaintainerConfig,
    selected: list[Check],
    log_dir: Path | None = None,
    runtime_events: CheckRuntimeEvents | None = None,
) -> list[CheckResult]:
    """Run selected checks after validating layout requirements."""

    selected_log_dir = log_dir or log_dir_for(config)
    if runtime_events is not None:
        runtime_events.selected(selected)
    layout = layout_failures(config, args.profile)
    if layout:
        return [emit_layout_failure(layout, selected_log_dir)]
    invalid_refs = ref_failures(
        Path.cwd(),
        base_ref=args.base_ref,
        compare_branch=args.compare_branch,
        validate_compare_branch=args.profile == CI_PROFILE,
    )
    if invalid_refs:
        return [emit_ref_failure(list(invalid_refs), selected_log_dir)]
    return _run_selected_checks(args, selected, selected_log_dir, runtime_events)


def _run_selected_checks(
    args: argparse.Namespace,
    selected: list[Check],
    selected_log_dir: Path,
    runtime_events: CheckRuntimeEvents | None,
) -> list[CheckResult]:
    """Run selected checks with runtime event instrumentation."""
    results: list[CheckResult] = []
    for check in selected:
        results.append(_run_one_check(args, check, selected_log_dir, runtime_events))
    return results


def _run_one_check(
    args: argparse.Namespace,
    check: Check,
    selected_log_dir: Path,
    runtime_events: CheckRuntimeEvents | None,
) -> CheckResult:
    """Run one check with runtime event instrumentation."""
    if runtime_events is not None:
        runtime_events.check_started(check)
    try:
        result = run_check(check, selected_log_dir, args.max_lines, args.max_chars)
    except Exception as exc:
        if runtime_events is not None:
            runtime_events.check_exception(check, exc)
        raise
    if runtime_events is not None:
        runtime_events.check_finished(result)
    return result


def write_artifacts_if_enabled(
    args: argparse.Namespace,
    config: MaintainerConfig,
    log_dir: Path,
    results: list[CheckResult],
    *,
    options: ArtifactWriteOptions,
) -> None:
    """Write verifier artifacts when diagnostics are enabled."""

    if not config.diagnostic_artifacts_enabled:
        return
    write_run_artifacts(
        log_dir,
        RunContext(
            repo_root=Path.cwd(),
            profile=args.profile,
            base_ref=args.base_ref,
            compare_branch=args.compare_branch,
            staged=args.staged,
            config=config,
            run_id=options.run_id,
        ),
        results,
        runtime_events=options.runtime_events,
    )
