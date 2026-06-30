"""Result summarization for quiet verifier runs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.core.reporting import print_failures, print_success
from agent_maintainer.models import CheckResult
from agent_maintainer.verify import timing as verify_timing


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
        context_log_dir=context_log_dir_value,
        run_details=details,
    )
    return 1


def run_details(
    profile: str,
    results: list[CheckResult],
    run_id: str | None,
) -> tuple[str, ...]:
    """Return compact run metadata lines for terminal output."""

    timing = verify_timing.run_timing(results)
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
