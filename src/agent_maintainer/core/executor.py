"""Command execution and log handling for maintainer checks."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from agent_maintainer.core import check_run as check_run_module
from agent_maintainer.core import reporting
from agent_maintainer.core.artifact_environment import artifact_environment
from agent_maintainer.core.command_environment import (
    command_env,
    tool_search_path,
)
from agent_maintainer.core.command_run import run_command_bounded
from agent_maintainer.core.tooling import capabilities as maintainer_tool_capabilities
from agent_maintainer.models import (
    SKIP_STATUS_DISABLED,
    SKIP_STATUS_MISSING_OPTIONAL,
    SKIP_STATUS_NOT_APPLICABLE,
    SKIP_STATUS_REQUIRED,
    SKIP_STATUS_UNSAFE_CONFIG,
    SKIP_STATUSES,
    Check,
    CheckResult,
)

OutputLimits = tuple[int, int]


def optional_skip(check: Check) -> str | None:
    """Return an optional-skip message when a configured integration is inactive."""

    if check.optional_skip_reason and optional_skip_applies(check):
        return f"optional skip: {check.optional_skip_reason}"
    return None


def optional_skip_status(check: Check) -> str:
    """Return stable skipped status for optional-skip artifacts."""
    if (
        check.optional_skip_status != SKIP_STATUS_DISABLED
        and check.optional_skip_status in SKIP_STATUSES
    ):
        return check.optional_skip_status
    reason = (check.optional_skip_reason or "").lower()
    status_markers = (
        (SKIP_STATUS_REQUIRED, (("require_tests = false",), ("tests are disabled",))),
        (SKIP_STATUS_UNSAFE_CONFIG, (("active environment",), ("without pinned input",))),
        (SKIP_STATUS_NOT_APPLICABLE, (("no ", " files matched"),)),
        (
            SKIP_STATUS_MISSING_OPTIONAL,
            (("absent",), ("not configured",), ("no schema",)),
        ),
    )
    for status, marker_groups in status_markers:
        if any(all(marker in reason for marker in group) for group in marker_groups):
            return status
    return SKIP_STATUS_DISABLED


def optional_skip_applies(check: Check) -> bool:
    """Return whether a check should report its configured optional skip."""

    if check.name == "import-linter":
        return not Path(".importlinter").exists()
    if check.name in {"tach", "tach-config", "architecture-decision"}:
        return not Path("tach.toml").exists()
    if check.name in {"actionlint", "zizmor"}:
        return not Path(".github/workflows").exists()
    policy_paths = {
        "contract-compatibility": ".agent-maintainer/contracts.toml",
        "verification-plan-policy": ".agent-maintainer/path-risk.toml",
    }
    configured_path = policy_paths.get(check.name)
    if configured_path is not None:
        return not Path(configured_path).exists()
    return check.name in {
        "pip-audit",
        "pytest-coverage",
        "diff-cover",
        "osv-scanner",
        "trivy",
        "sbom",
        "license-check",
        "secret-scan",
        "secret-scan-history",
        "wemake",
        "interrogate",
    }


def missing_requirement(check: Check) -> str | None:
    """Return a user-facing reason a check cannot run, if any."""

    optional = optional_skip(check)
    if optional:
        return optional
    for required_path in check.required_paths:
        if not Path(required_path).exists():
            return f"required path {required_path!r} is absent"
    if (
        check.required_executable
        and shutil.which(check.required_executable, path=tool_search_path()) is None
    ):
        return maintainer_tool_capabilities.missing_executable_message(check.required_executable)
    return None


def run_command(
    command: list[str],
    *,
    timeout_seconds: int | None = None,
    output_limit_chars: int | None = None,
) -> tuple[int, str]:
    """Run a command and combine stdout and stderr for log storage."""

    return run_command_bounded(
        command,
        env=command_env(),
        timeout_seconds=timeout_seconds,
        output_limit_chars=output_limit_chars,
    )


def run_check(check: Check, log_dir: Path, max_lines: int, max_chars: int) -> CheckResult:
    """Execute one check, write its raw log, and return a compact result."""

    log_path = log_dir / f"{check.name}.log"
    started_at = check_run_module.utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    missing = missing_requirement(check)
    if missing:
        return missing_requirement_result(check, log_path, missing, started_at)
    try:
        with artifact_environment(log_dir):
            returncode, output = run_command(
                check.command,
                timeout_seconds=check.timeout_seconds,
                output_limit_chars=check.output_limit_chars,
            )
            capture_stdout_artifact(check, output)
    except OSError as exc:
        ended_at = check_run_module.utc_timestamp()
        output = f"could not run {check.command!r}: {exc}"
        log_path.write_text(f"{output}\n", encoding="utf-8")
        return CheckResult(
            check.name,
            passed=False,
            output=output,
            command=tuple(check.command),
            log_path=str(log_path),
            started_at=started_at,
            ended_at=ended_at,
            artifact_sensitivity=check.artifact_sensitivity,
            structured_parser=check.structured_parser,
            structured_parser_manager=check.structured_parser_manager,
        )
    ended_at = check_run_module.utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    artifact_paths = existing_artifact_paths(check)
    if returncode == 0:
        return success_result(
            check,
            output,
            (max_lines, max_chars),
            check_run_module.CheckRun(log_path, started_at, ended_at),
        )
    return CheckResult(
        check.name,
        passed=False,
        output=reporting.summarize_check_from_artifacts(
            check.name,
            artifact_paths,
            output,
            max_lines,
            max_chars,
            structured_parser=check.structured_parser,
            structured_parser_manager=check.structured_parser_manager,
        ),
        command=tuple(check.command),
        exit_code=returncode,
        log_path=str(log_path),
        started_at=started_at,
        ended_at=ended_at,
        artifact_paths=artifact_paths,
        artifact_sensitivity=check.artifact_sensitivity,
        structured_parser=check.structured_parser,
        structured_parser_manager=check.structured_parser_manager,
    )


def existing_artifact_paths(check: Check) -> tuple[str, ...]:
    """Return declared artifacts that exist after a check has run."""

    return tuple(path for path in check.artifact_paths if Path(path).exists())


def capture_stdout_artifact(check: Check, output: str) -> None:
    """Retain complete JSON stdout for the contract compatibility check."""

    if check.name != "contract-compatibility" or len(check.artifact_paths) != 1:
        return
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    path = Path(check.artifact_paths[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")


def missing_requirement_result(
    check: Check, log_path: Path, missing: str, started_at: str
) -> CheckResult:
    """Write a missing-requirement log and return its verifier result."""

    ended_at = check_run_module.utc_timestamp()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"{missing}\n", encoding="utf-8")
    if missing.startswith("optional skip:"):
        return CheckResult(
            check.name,
            passed=True,
            output=missing.removeprefix("optional skip: "),
            skipped=True,
            skip_status=optional_skip_status(check),
            command=tuple(check.command),
            log_path=str(log_path),
            started_at=started_at,
            ended_at=ended_at,
            artifact_sensitivity=check.artifact_sensitivity,
            structured_parser=check.structured_parser,
            structured_parser_manager=check.structured_parser_manager,
        )
    return CheckResult(
        check.name,
        passed=False,
        output=missing,
        command=tuple(check.command),
        log_path=str(log_path),
        started_at=started_at,
        ended_at=ended_at,
        artifact_sensitivity=check.artifact_sensitivity,
        structured_parser=check.structured_parser,
        structured_parser_manager=check.structured_parser_manager,
    )


def success_result(
    check: Check,
    output: str,
    output_limits: OutputLimits,
    check_run: check_run_module.CheckRun,
) -> CheckResult:
    """Return a passing result, preserving configured warning output."""

    artifact_paths = existing_artifact_paths(check)
    if check.report_success_output and output.strip():
        max_lines, max_chars = output_limits
        return CheckResult(
            check.name,
            passed=True,
            output=reporting.summarize_check(
                check.name,
                output,
                max_lines,
                max_chars,
                structured_parser=check.structured_parser,
                structured_parser_manager=check.structured_parser_manager,
            ),
            warning=True,
            command=tuple(check.command),
            exit_code=0,
            log_path=str(check_run.log_path),
            started_at=check_run.started_at,
            ended_at=check_run.ended_at,
            artifact_paths=artifact_paths,
            artifact_sensitivity=check.artifact_sensitivity,
            structured_parser=check.structured_parser,
            structured_parser_manager=check.structured_parser_manager,
        )
    return CheckResult(
        check.name,
        passed=True,
        command=tuple(check.command),
        exit_code=0,
        log_path=str(check_run.log_path),
        started_at=check_run.started_at,
        ended_at=check_run.ended_at,
        artifact_paths=artifact_paths,
        artifact_sensitivity=check.artifact_sensitivity,
        structured_parser=check.structured_parser,
        structured_parser_manager=check.structured_parser_manager,
    )
