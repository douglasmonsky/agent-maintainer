"""Command execution and log handling for guardrail checks."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts import guardrail_tool_capabilities
from scripts.guardrail_models import Check, CheckResult
from scripts.guardrail_reporting import summarize_check

OutputLimits = tuple[int, int]


@dataclass(frozen=True)
class CheckRun:
    """Metadata captured for one check execution."""

    log_path: Path
    started_at: str
    ended_at: str


def utc_timestamp() -> str:
    """Return a stable UTC timestamp for verifier metadata."""

    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def tool_search_path() -> str:
    """Build PATH with local virtualenv tools ahead of ambient executables."""

    local_tool_dirs = [
        str(Path(relative)) for relative in (".venv/bin", "venv/bin") if Path(relative).is_dir()
    ]
    executable_dir = str(Path(sys.executable).parent)
    existing_path = os.environ.get("PATH", "")
    search_dirs = [*local_tool_dirs, executable_dir]
    if existing_path:
        search_dirs.append(existing_path)
    return os.pathsep.join(search_dirs)


def command_env() -> dict[str, str]:
    """Return the subprocess environment used for guardrail commands."""

    env = os.environ.copy()
    env["PATH"] = tool_search_path()
    return env


def optional_skip(check: Check) -> str | None:
    """Return an optional-skip message when a configured integration is inactive."""

    if check.optional_skip_reason and optional_skip_applies(check):
        return f"optional skip: {check.optional_skip_reason}"
    return None


def optional_skip_applies(check: Check) -> bool:
    """Return whether a check should report its configured optional skip."""

    if check.name == "import-linter":
        return not Path(".importlinter").exists()
    if check.name in {"tach", "tach-config"}:
        return not Path("tach.toml").exists()
    if check.name in {"actionlint", "zizmor"}:
        return not Path(".github/workflows").exists()
    return check.name in {
        "pip-audit",
        "pytest-coverage",
        "diff-cover",
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
        return guardrail_tool_capabilities.missing_executable_message(check.required_executable)
    return None


def run_command(command: list[str]) -> tuple[int, str]:
    """Run a command and combine stdout and stderr for log storage."""

    result = subprocess.run(  # nosec B603
        command,
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    return result.returncode, "\n".join(part for part in (result.stdout, result.stderr) if part)


def run_check(check: Check, log_dir: Path, max_lines: int, max_chars: int) -> CheckResult:
    """Execute one check, write its raw log, and return a compact result."""

    log_path = log_dir / f"{check.name}.log"
    started_at = utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    missing = missing_requirement(check)
    if missing:
        return missing_requirement_result(check, log_path, missing, started_at)
    try:
        returncode, output = run_command(check.command)
    except OSError as exc:
        ended_at = utc_timestamp()
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
        )
    ended_at = utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    artifact_paths = existing_artifact_paths(check)
    if returncode == 0:
        return success_result(
            check,
            output,
            (max_lines, max_chars),
            CheckRun(log_path, started_at, ended_at),
        )
    return CheckResult(
        check.name,
        passed=False,
        output=summarize_check(check.name, output, max_lines, max_chars),
        command=tuple(check.command),
        exit_code=returncode,
        log_path=str(log_path),
        started_at=started_at,
        ended_at=ended_at,
        artifact_paths=artifact_paths,
    )


def existing_artifact_paths(check: Check) -> tuple[str, ...]:
    """Return declared artifacts that exist after a check has run."""

    return tuple(path for path in check.artifact_paths if Path(path).exists())


def missing_requirement_result(
    check: Check, log_path: Path, missing: str, started_at: str
) -> CheckResult:
    """Write a missing-requirement log and return its verifier result."""

    ended_at = utc_timestamp()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"{missing}\n", encoding="utf-8")
    if missing.startswith("optional skip:"):
        return CheckResult(
            check.name,
            passed=True,
            output=missing.removeprefix("optional skip: "),
            skipped=True,
            command=tuple(check.command),
            log_path=str(log_path),
            started_at=started_at,
            ended_at=ended_at,
        )
    return CheckResult(
        check.name,
        passed=False,
        output=missing,
        command=tuple(check.command),
        log_path=str(log_path),
        started_at=started_at,
        ended_at=ended_at,
    )


def success_result(
    check: Check,
    output: str,
    output_limits: OutputLimits,
    check_run: CheckRun,
) -> CheckResult:
    """Return a passing result, preserving configured warning output."""

    artifact_paths = existing_artifact_paths(check)
    if check.report_success_output and output.strip():
        max_lines, max_chars = output_limits
        return CheckResult(
            check.name,
            passed=True,
            output=summarize_check(check.name, output, max_lines, max_chars),
            warning=True,
            command=tuple(check.command),
            exit_code=0,
            log_path=str(check_run.log_path),
            started_at=check_run.started_at,
            ended_at=check_run.ended_at,
            artifact_paths=artifact_paths,
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
    )
