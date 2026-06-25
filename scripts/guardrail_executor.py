"""Command execution and log handling for guardrail checks."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts.guardrail_models import Check, CheckResult
from scripts.guardrail_reporting import summarize_check


def tool_search_path() -> str:
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
    env = os.environ.copy()
    env["PATH"] = tool_search_path()
    return env


def optional_skip(check: Check) -> str | None:
    if not check.optional_skip_reason:
        return None
    if check.name == "import-linter" and not Path(".importlinter").exists():
        return f"optional skip: {check.optional_skip_reason}"
    if check.name in {"tach", "tach-config"} and not Path("tach.toml").exists():
        return f"optional skip: {check.optional_skip_reason}"
    if check.name in {"pip-audit", "pytest-coverage", "diff-cover", "wemake", "interrogate"}:
        return f"optional skip: {check.optional_skip_reason}"
    return None


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
        return f"command not found: {check.required_executable!r}. Install dev dependencies."
    return None


def run_command(command: list[str]) -> tuple[int, str]:
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

    missing = missing_requirement(check)
    if missing:
        log_dir.mkdir(exist_ok=True)
        (log_dir / f"{check.name}.log").write_text(f"{missing}\n", encoding="utf-8")
        if missing.startswith("optional skip:"):
            return CheckResult(
                check.name,
                passed=True,
                output=missing.removeprefix("optional skip: "),
                skipped=True,
            )
        return CheckResult(check.name, passed=False, output=missing)
    try:
        returncode, output = run_command(check.command)
    except OSError as exc:
        return CheckResult(
            check.name, passed=False, output=f"could not run {check.command!r}: {exc}"
        )
    log_dir.mkdir(exist_ok=True)
    (log_dir / f"{check.name}.log").write_text(output, encoding="utf-8")
    if returncode == 0:
        return CheckResult(check.name, passed=True)
    return CheckResult(
        check.name,
        passed=False,
        output=summarize_check(check.name, output, max_lines, max_chars),
    )
