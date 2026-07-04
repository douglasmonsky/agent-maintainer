"""Verifier run steps shared by quiet CLI orchestration."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.core.check_run import utc_timestamp
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.core.executor import run_check
from agent_maintainer.core.layout import layout_failures
from agent_maintainer.models import CI_PROFILE, Check, CheckResult
from agent_maintainer.verify.artifacts import RunContext, write_run_artifacts
from agent_maintainer.verify.git_refs import ref_failures


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
) -> list[CheckResult]:
    """Run selected checks after validating layout requirements."""

    selected_log_dir = log_dir or log_dir_for(config)
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
    return [
        run_check(check, selected_log_dir, args.max_lines, args.max_chars) for check in selected
    ]


def write_artifacts_if_enabled(
    args: argparse.Namespace,
    config: MaintainerConfig,
    log_dir: Path,
    results: list[CheckResult],
    run_id: str,
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
            run_id=run_id,
        ),
        results,
    )
