"""Result summarization for quiet verifier runs."""

from __future__ import annotations

import shlex
from dataclasses import replace
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.core.reporting import print_failures, print_success
from agent_maintainer.models import CheckResult
from agent_run_artifacts import models as artifact_models
from agent_run_artifacts import timing as verify_timing


def artifact_check_result(result: CheckResult) -> artifact_models.ArtifactCheckResult:
    """Return run-artifact check DTO from verifier result."""

    return artifact_models.ArtifactCheckResult(
        name=result.name,
        passed=result.passed,
        output=result.output,
        command=tuple(result.command),
        exit_code=result.exit_code,
        log_path=result.log_path,
        warning=result.warning,
        skipped=result.skipped,
        skip_status=result.skip_status,
        started_at=result.started_at,
        ended_at=result.ended_at,
        artifact_paths=tuple(result.artifact_paths),
        artifact_sensitivity=result.artifact_sensitivity,
    )


def apply_optional_skip_policy(
    results: list[CheckResult], fail_on_optional_skip: bool
) -> list[CheckResult]:
    """Convert skips into failures when the caller asks for strictness."""

    if not fail_on_optional_skip:
        return results
    return [
        (
            replace(
                result,
                passed=False,
                output=f"optional check skipped: {result.output}",
                skipped=False,
            )
            if result.skipped
            else result
        )
        for result in results
    ]


def print_result_summary(
    profile: str,
    results: list[CheckResult],
    *,
    context_log_dir_value: str | None = None,
    run_id: str | None = None,
) -> int:
    """Print compact verifier result and return the process exit code."""

    failures = [result for result in results if not result.passed]
    skipped = [result for result in results if result.skipped]
    warnings = [result for result in results if result.warning]
    details = run_details(profile, results, run_id)

    if not failures:
        print_success(skipped, warnings, run_details=details)
        return 0

    print_failures(
        profile,
        failures,
        skipped,
        run_details=details,
        footer=(context_log_dir_value, smallest_rerun_command(profile, failures)),
    )
    return 1


def smallest_rerun_command(profile: str, failures: list[CheckResult]) -> str:
    """Return smallest useful command after verifier failure."""

    if len(failures) == 1 and failures[0].command:
        return " ".join(shlex.quote(part) for part in failures[0].command)
    return f"python3 -m agent_maintainer verify --profile {profile}"


def run_details(
    profile: str,
    results: list[CheckResult],
    run_id: str | None,
) -> tuple[str, ...]:
    """Return compact run metadata lines for terminal output."""

    artifact_results = tuple(artifact_check_result(result) for result in results)
    timing = verify_timing.run_timing(artifact_results)
    duration = timing.get("duration_seconds")
    duration_text = verify_timing.format_duration(
        duration if isinstance(duration, int | float) else None
    )
    details = [f"Profile: {profile}"]
    if run_id:
        details.append(f"Run ID: {run_id}")
    details.append(f"Duration: {duration_text} ({verify_timing.profile_duration_hint(profile)})")
    return tuple(details)


def context_log_dir(config: MaintainerConfig, log_dir: Path, run_id: str) -> str | None:
    """Return stable context log directory for just-in-time commands."""

    if not config.diagnostic_artifacts_enabled or config.diagnostic_run_history_limit <= 0:
        return None
    return str(log_dir / "runs" / run_id)
