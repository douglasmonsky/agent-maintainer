"""Setup and health diagnostics for the guardrail kit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.guardrail_catalog import make_checks
from scripts.guardrail_config import (
    FRESH_STRICT_MODE,
    TACH_TOOL,
    GuardrailConfig,
    format_paths,
    load_config,
)
from scripts.guardrail_layout import layout_failures
from scripts.guardrail_tach import tach_config_issues

Status = str

OK: Status = "PASS"
WARNING: Status = "WARN"
ERROR: Status = "FAIL"
MIN_PYTHON = (3, 11)
VERIFY_LOG_DIR = ".verify-logs"


@dataclass(frozen=True)
class DoctorResult:
    name: str
    status: Status
    message: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when any warning is present.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable diagnostic results.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    results = run_doctor(Path.cwd(), load_config())
    if args.json:
        print(json.dumps([item.__dict__ for item in results], indent=2))
    else:
        print_text(results)
    return status_code(results, strict=args.strict)


def run_doctor(repo_root: Path, config: GuardrailConfig) -> list[DoctorResult]:
    return [
        check_python_version(),
        check_repo_root(repo_root),
        check_virtualenv(repo_root),
        check_required_executables(repo_root, config),
        check_layout(config),
        check_tests(repo_root, config),
        check_pre_commit(repo_root),
        check_codex_hooks(repo_root),
        check_optional_gates(repo_root, config),
        check_canonical_commands(repo_root),
        check_git_state(repo_root),
        check_recent_logs(repo_root),
    ]


def check_python_version() -> DoctorResult:
    version = sys.version_info
    detected = f"{version.major}.{version.minor}.{version.micro}"
    if (version.major, version.minor) < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        return DoctorResult(
            "python-version",
            ERROR,
            f"Python {detected}; Python {required}+ is required.",
        )
    return DoctorResult("python-version", OK, f"Python {detected}")


def check_repo_root(repo_root: Path) -> DoctorResult:
    missing = [path for path in (".git", "scripts/guardrail.py") if not (repo_root / path).exists()]
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult("repo-root", ERROR, f"Missing required repo paths: {missing_paths}")
    if not (repo_root / "pyproject.toml").exists():
        return DoctorResult(
            "repo-root", WARNING, "pyproject.toml is absent; defaults will be used."
        )
    return DoctorResult("repo-root", OK, str(repo_root))


def check_virtualenv(repo_root: Path) -> DoctorResult:
    for relative in (".venv/bin/python", "venv/bin/python"):
        if (repo_root / relative).exists():
            return DoctorResult("virtualenv", OK, relative)
    return DoctorResult("virtualenv", WARNING, "No .venv or venv Python found.")


def check_required_executables(repo_root: Path, config: GuardrailConfig) -> DoctorResult:
    checks = make_checks(config, "HEAD", "origin/main")
    required = sorted({check.required_executable for check in checks if check.required_executable})
    missing = [name for name in required if not executable_exists(repo_root, name)]
    if missing:
        missing_names = ", ".join(missing)
        return DoctorResult("required-executables", ERROR, f"Missing: {missing_names}")
    return DoctorResult("required-executables", OK, f"Found {len(required)} executables.")


def executable_exists(repo_root: Path, executable: str) -> bool:
    local_paths = (
        repo_root / ".venv" / "bin" / executable,
        repo_root / "venv" / "bin" / executable,
    )
    return any(path.exists() for path in local_paths) or shutil.which(executable) is not None


def check_layout(config: GuardrailConfig) -> DoctorResult:
    failures = layout_failures(config, "full")
    if failures:
        return DoctorResult("configured-roots", ERROR, "; ".join(failures))
    source_roots = format_paths(config.source_roots)
    test_roots = format_paths(config.test_roots)
    return DoctorResult("configured-roots", OK, f"sources={source_roots}; tests={test_roots}")


def check_tests(repo_root: Path, config: GuardrailConfig) -> DoctorResult:
    if not config.require_tests:
        return DoctorResult("tests", WARNING, "Tests are disabled with require_tests = false.")
    existing = [path for path in config.test_roots if (repo_root / path).exists()]
    if not existing:
        test_roots = format_paths(config.test_roots)
        return DoctorResult(
            "tests",
            ERROR,
            f"No configured test roots exist: {test_roots}",
        )
    existing_roots = ", ".join(existing)
    return DoctorResult("tests", OK, f"Configured test roots exist: {existing_roots}")


def check_pre_commit(repo_root: Path) -> DoctorResult:
    config_path = repo_root / ".pre-commit-config.yaml"
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"
    if not config_path.exists():
        return DoctorResult("pre-commit-hook", WARNING, ".pre-commit-config.yaml is absent.")
    if not hook_path.exists():
        return DoctorResult("pre-commit-hook", WARNING, "pre-commit hook is not installed.")
    return DoctorResult("pre-commit-hook", OK, ".git/hooks/pre-commit is installed.")


def check_codex_hooks(repo_root: Path) -> DoctorResult:
    config_path = repo_root / ".codex" / "config.toml"
    if not config_path.exists():
        return DoctorResult("codex-hooks", WARNING, ".codex/config.toml is absent.")
    text = config_path.read_text(encoding="utf-8")
    if "hooks = true" not in text:
        return DoctorResult("codex-hooks", WARNING, ".codex/config.toml does not enable hooks.")
    return DoctorResult("codex-hooks", OK, ".codex/config.toml enables hooks.")


def check_optional_gates(repo_root: Path, config: GuardrailConfig) -> DoctorResult:
    missing: list[str] = []
    architecture_name = "Import Linter"
    if config.architecture_tool == TACH_TOOL:
        architecture_name = "Tach"
        missing.extend(
            tach_config_issues(repo_root, require_strict_root=config.mode == FRESH_STRICT_MODE)
        )
    elif not (repo_root / ".importlinter").exists():
        missing.append(".importlinter")
    if not config.enable_pip_audit:
        missing.append("pip-audit disabled")
    if not config.enable_wemake:
        missing.append("wemake disabled")
    if missing:
        return DoctorResult("optional-gates", WARNING, "; ".join(missing))
    return DoctorResult(
        "optional-gates", OK, f"{architecture_name}, pip-audit, and wemake are active."
    )


def check_canonical_commands(repo_root: Path) -> DoctorResult:
    expectations = {
        ".github/workflows/verify.yml": "python3 -m scripts.guardrail verify",
        ".pre-commit-config.yaml": "python3 -m scripts.guardrail verify --profile precommit",
        ".codex/hooks/post_edit_fast_gate.py": "scripts.guardrail",
        ".codex/hooks/stop_full_verify.py": "scripts.guardrail",
    }
    missing = [path for path in expectations if not (repo_root / path).exists()]
    stale = [
        path
        for path, needle in expectations.items()
        if (repo_root / path).exists()
        and needle not in (repo_root / path).read_text(encoding="utf-8")
    ]
    if stale:
        stale_paths = ", ".join(stale)
        return DoctorResult("canonical-commands", ERROR, f"Stale command path in: {stale_paths}")
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "canonical-commands", WARNING, f"Missing command files: {missing_paths}"
        )
    return DoctorResult(
        "canonical-commands",
        OK,
        "CI, pre-commit, and Codex hooks use module entrypoint.",
    )


def check_git_state(repo_root: Path) -> DoctorResult:
    git_path = shutil.which("git")
    if git_path is None:
        return DoctorResult("git-state", WARNING, "git executable was not found.")

    completed = subprocess.run(  # nosec B603
        [git_path, "status", "--short", "--branch"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return DoctorResult("git-state", WARNING, (completed.stderr or "git status failed").strip())
    lines = completed.stdout.splitlines()
    branch = lines[0] if lines else "## unknown"
    details = []
    if "[ahead" in branch or "[behind" in branch:
        details.append(branch.removeprefix("## "))
    if len(lines) > 1:
        changed_count = len(lines) - 1
        details.append(f"{changed_count} changed path(s)")
    if details:
        return DoctorResult("git-state", WARNING, "; ".join(details))
    return DoctorResult("git-state", OK, branch.removeprefix("## "))


def check_recent_logs(repo_root: Path) -> DoctorResult:
    log_dir = repo_root / VERIFY_LOG_DIR
    if not log_dir.exists():
        return DoctorResult("verification-logs", WARNING, f"{VERIFY_LOG_DIR}/ is absent.")
    logs = sorted(log_dir.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not logs:
        return DoctorResult("verification-logs", WARNING, f"No logs found in {VERIFY_LOG_DIR}/.")
    latest_log = logs[0].name
    return DoctorResult("verification-logs", OK, f"Latest log: {latest_log}")


def print_text(results: list[DoctorResult]) -> None:
    for item in results:
        print(f"{item.status} {item.name}: {item.message}")


def status_code(results: list[DoctorResult], *, strict: bool) -> int:
    if any(item.status == ERROR for item in results):
        return 1
    if strict and any(item.status == WARNING for item in results):
        return 1
    return 0
