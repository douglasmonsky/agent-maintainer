"""Setup and health diagnostics for the guardrail kit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts import (
    guardrail_config,
    guardrail_doctor_hook_audit,
    guardrail_doctor_logs,
    guardrail_doctor_policy,
    guardrail_guidance,
    guardrail_tool_capabilities,
)
from scripts.guardrail_catalog import make_checks
from scripts.guardrail_doctor_models import ERROR, OK, WARNING, DoctorResult
from scripts.guardrail_layout import layout_failures
from scripts.guardrail_tach import tach_config_issues

MIN_PYTHON = (3, 11)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse doctor command-line options."""

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
    """Run setup diagnostics and emit text or JSON output."""

    args = parse_args(argv)
    results = run_doctor(Path.cwd(), guardrail_config.load_config())
    if args.json:
        print(json.dumps([item.__dict__ for item in results], indent=2))
    else:
        print_text(results)
    return status_code(results, strict=args.strict)


def run_doctor(repo_root: Path, config: guardrail_config.GuardrailConfig) -> list[DoctorResult]:
    """Run every setup diagnostic against a repository root."""

    return [
        check_python_version(),
        check_repo_root(repo_root),
        check_virtualenv(repo_root),
        check_tool_capabilities(repo_root, config),
        check_layout(config),
        check_tests(repo_root, config),
        guardrail_doctor_policy.check_pyright_config(repo_root, config),
        check_pre_commit(repo_root),
        check_codex_hooks(repo_root),
        guardrail_doctor_hook_audit.check_hook_audit(repo_root, config),
        guardrail_doctor_policy.check_pip_audit_safety(config),
        guardrail_doctor_policy.check_secret_scanning_policy(config),
        check_optional_gates(repo_root, config),
        check_canonical_commands(repo_root),
        check_agent_guidance(repo_root, config),
        check_git_state(repo_root),
        guardrail_doctor_logs.check_recent_logs(repo_root, config),
    ]


def check_python_version() -> DoctorResult:
    """Check that the active Python runtime satisfies the verifier minimum."""

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
    """Check for files that identify a usable guardrail repository root."""

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
    """Report whether a local virtualenv is available for tool execution."""

    for relative in (".venv/bin/python", "venv/bin/python"):
        if (repo_root / relative).exists():
            return DoctorResult("virtualenv", OK, relative)
    return DoctorResult("virtualenv", WARNING, "No .venv or venv Python found.")


def check_tool_capabilities(
    repo_root: Path, config: guardrail_config.GuardrailConfig
) -> DoctorResult:
    """Check active tool capabilities without conflating disabled integrations."""

    checks = make_checks(config, "HEAD", "origin/main")
    states = [
        *guardrail_tool_capabilities.states_for_checks(repo_root, checks),
        *guardrail_tool_capabilities.local_runtime_states(repo_root),
    ]
    state, message = guardrail_tool_capabilities.summarize_states(states)
    status = ERROR if state == guardrail_tool_capabilities.MISSING else OK
    return DoctorResult("tool-capabilities", status, message)


def check_layout(config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Validate configured source, package, test, and coverage roots."""

    failures = layout_failures(config, "full")
    if failures:
        return DoctorResult("configured-roots", ERROR, "; ".join(failures))
    source_roots = guardrail_config.format_paths(config.source_roots)
    test_roots = guardrail_config.format_paths(config.test_roots)
    return DoctorResult("configured-roots", OK, f"sources={source_roots}; tests={test_roots}")


def check_tests(repo_root: Path, config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Report whether tests are required and available."""

    if not config.require_tests:
        return DoctorResult("tests", WARNING, "Tests are disabled with require_tests = false.")
    existing = [path for path in config.test_roots if (repo_root / path).exists()]
    if not existing:
        test_roots = guardrail_config.format_paths(config.test_roots)
        return DoctorResult(
            "tests",
            ERROR,
            f"No configured test roots exist: {test_roots}",
        )
    existing_roots = ", ".join(existing)
    return DoctorResult("tests", OK, f"Configured test roots exist: {existing_roots}")


def check_pre_commit(repo_root: Path) -> DoctorResult:
    """Report whether the pre-commit config and hook are installed."""

    config_path = repo_root / ".pre-commit-config.yaml"
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"
    if not config_path.exists():
        return DoctorResult("pre-commit-hook", WARNING, ".pre-commit-config.yaml is absent.")
    if not hook_path.exists():
        return DoctorResult("pre-commit-hook", WARNING, "pre-commit hook is not installed.")
    return DoctorResult("pre-commit-hook", OK, ".git/hooks/pre-commit is installed.")


def check_codex_hooks(repo_root: Path) -> DoctorResult:
    """Report whether repo-local Codex hooks are configured."""

    config_path = repo_root / ".codex" / "config.toml"
    if not config_path.exists():
        return DoctorResult("codex-hooks", WARNING, ".codex/config.toml is absent.")
    text = config_path.read_text(encoding="utf-8")
    if "hooks = true" not in text:
        return DoctorResult("codex-hooks", WARNING, ".codex/config.toml does not enable hooks.")
    return DoctorResult("codex-hooks", OK, ".codex/config.toml enables hooks.")


def check_optional_gates(repo_root: Path, config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Report whether optional hardening integrations are active."""

    missing: list[str] = []
    architecture_name = "Import Linter"
    if config.architecture_tool == guardrail_config.TACH_TOOL:
        architecture_name = "Tach"
        missing.extend(
            tach_config_issues(
                repo_root,
                require_strict_root=config.mode == guardrail_config.FRESH_STRICT_MODE,
            )
        )
    elif not (repo_root / ".importlinter").exists():
        missing.append(".importlinter")
    if not config.enable_pip_audit:
        missing.append("pip-audit disabled")
    if not config.enable_wemake:
        missing.append("wemake disabled")
    if not config.enable_interrogate:
        missing.append("interrogate disabled")
    if missing:
        return DoctorResult("optional-gates", WARNING, "; ".join(missing))
    return DoctorResult(
        "optional-gates",
        OK,
        f"{architecture_name}, pip-audit, wemake, and interrogate are active.",
    )


def check_canonical_commands(repo_root: Path) -> DoctorResult:
    """Check that CI, pre-commit, and hooks use the module entrypoint."""

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


def check_agent_guidance(repo_root: Path, config: guardrail_config.GuardrailConfig) -> DoctorResult:
    """Report whether generated agent guidance matches current config."""

    state = guardrail_guidance.guidance_state(repo_root, config)
    if state.status == "current":
        return DoctorResult("agent-guidance", OK, state.message)
    status = ERROR if config.mode == guardrail_config.FRESH_STRICT_MODE else WARNING
    return DoctorResult("agent-guidance", status, state.message)


def check_git_state(repo_root: Path) -> DoctorResult:
    """Summarize dirty, ahead, or behind Git state."""

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


def print_text(results: list[DoctorResult]) -> None:
    """Print doctor results as compact PASS/WARN/FAIL rows."""

    for item in results:
        print(f"{item.status} {item.name}: {item.message}")


def status_code(results: list[DoctorResult], *, strict: bool) -> int:
    """Return the doctor process status for default or strict mode."""

    if any(item.status == ERROR for item in results):
        return 1
    if strict and any(item.status == WARNING for item in results):
        return 1
    return 0
