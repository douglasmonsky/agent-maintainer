"""Setup and health diagnostics for the guardrail kit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

from ai_guardrails.core import config as guardrail_config
from ai_guardrails.doctor import setup as guardrail_doctor_setup
from ai_guardrails.doctor.support import hook_audit as guardrail_doctor_hook_audit
from ai_guardrails.doctor.support import logs as guardrail_doctor_logs
from ai_guardrails.doctor.support import models as guardrail_doctor_models
from ai_guardrails.doctor.support import policy as guardrail_doctor_policy

DoctorResult = guardrail_doctor_models.DoctorResult
ERROR = guardrail_doctor_models.ERROR
OK = guardrail_doctor_models.OK
WARNING = guardrail_doctor_models.WARNING

check_python_version = guardrail_doctor_setup.check_python_version
check_agent_guidance = guardrail_doctor_setup.check_agent_guidance
check_layout = guardrail_doctor_setup.check_layout
check_optional_gates = guardrail_doctor_setup.check_optional_gates
check_tests = guardrail_doctor_setup.check_tests
check_tool_capabilities = guardrail_doctor_setup.check_tool_capabilities


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
        guardrail_doctor_setup.check_architecture_backend(repo_root, config),
        check_layout(config),
        check_tests(repo_root, config),
        guardrail_doctor_setup.check_thresholds(config),
        guardrail_doctor_setup.check_structure_thresholds(config),
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


def check_repo_root(repo_root: Path) -> DoctorResult:
    """Check for files that identify a usable guardrail repository root."""

    missing = [
        path
        for path in (".git", "src/ai_guardrails/__main__.py")
        if not (repo_root / path).exists()
    ]
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "repo-root",
            ERROR,
            f"Missing required repo paths: {missing_paths}",
            state=guardrail_doctor_models.MISSING,
        )
    if not (repo_root / "pyproject.toml").exists():
        return DoctorResult(
            "repo-root",
            WARNING,
            "pyproject.toml is absent; defaults will be used.",
            state=guardrail_doctor_models.MISSING,
        )
    return DoctorResult("repo-root", OK, str(repo_root))


def check_virtualenv(repo_root: Path) -> DoctorResult:
    """Report whether a local virtualenv is available for tool execution."""

    for relative in (".venv/bin/python", "venv/bin/python"):
        if (repo_root / relative).exists():
            return DoctorResult("virtualenv", OK, relative)
    return DoctorResult(
        "virtualenv",
        WARNING,
        "No .venv or venv Python found.",
        state=guardrail_doctor_models.MISSING,
        hint="Run python3 -m ai_guardrails bootstrap.",
    )


def check_pre_commit(repo_root: Path) -> DoctorResult:
    """Report whether the pre-commit config and hook are installed."""

    config_path = repo_root / ".pre-commit-config.yaml"
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"
    if not config_path.exists():
        return DoctorResult(
            "pre-commit-hook",
            WARNING,
            ".pre-commit-config.yaml is absent.",
            state=guardrail_doctor_models.NOT_APPLICABLE,
        )
    if not hook_path.exists():
        return DoctorResult(
            "pre-commit-hook",
            WARNING,
            "pre-commit hook is not installed.",
            state=guardrail_doctor_models.MISSING,
            hint="Run python3 -m ai_guardrails install.",
        )
    return DoctorResult("pre-commit-hook", OK, ".git/hooks/pre-commit is installed.")


def check_codex_hooks(repo_root: Path) -> DoctorResult:
    """Report whether repo-local Codex hooks are configured."""

    config_path = repo_root / ".codex" / "config.toml"
    if not config_path.exists():
        return DoctorResult(
            "codex-hooks",
            WARNING,
            ".codex/config.toml is absent.",
            state=guardrail_doctor_models.MISSING,
            hint="Run python3 -m ai_guardrails install.",
        )
    text = config_path.read_text(encoding="utf-8")
    if "hooks = true" not in text:
        return DoctorResult(
            "codex-hooks",
            WARNING,
            ".codex/config.toml does not enable hooks.",
            state=guardrail_doctor_models.DISABLED,
            hint="Set hooks = true for this repo if Codex hooks should enforce guardrails.",
        )
    return DoctorResult("codex-hooks", OK, ".codex/config.toml enables hooks.")


def check_canonical_commands(repo_root: Path) -> DoctorResult:
    """Check that CI, pre-commit, and hooks use the module entrypoint."""

    expectations = {
        ".github/workflows/verify.yml": "python3 -m ai_guardrails verify",
        ".pre-commit-config.yaml": "python3 -m ai_guardrails verify --profile precommit",
        ".codex/hooks/post_edit_fast_gate.py": "ai_guardrails",
        ".codex/hooks/stop_full_verify.py": "ai_guardrails",
    }
    missing = [path for path in expectations if not (repo_root / path).exists()]
    stale = [
        path
        for path, needle in expectations.items()
        if (repo_root / path).exists()
        and normalized_text(needle)
        not in normalized_text((repo_root / path).read_text(encoding="utf-8"))
    ]
    if stale:
        stale_paths = ", ".join(stale)
        return DoctorResult(
            "canonical-commands",
            ERROR,
            f"Stale command path in: {stale_paths}",
            state=guardrail_doctor_models.UNSAFE_CONFIG,
            hint="Use python3 -m ai_guardrails in CI, pre-commit, and Codex hooks.",
        )
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "canonical-commands",
            WARNING,
            f"Missing command files: {missing_paths}",
            state=guardrail_doctor_models.MISSING,
            hint="Run python3 -m ai_guardrails install or add the missing integration files.",
        )
    return DoctorResult(
        "canonical-commands",
        OK,
        "CI, pre-commit, and Codex hooks use module entrypoint.",
    )


def normalized_text(text: str) -> str:
    """Return text normalized for command substring checks."""
    return " ".join(text.split())


def check_git_state(repo_root: Path) -> DoctorResult:
    """Summarize dirty, ahead, or behind Git state."""

    git_path = shutil.which("git")
    if git_path is None:
        return DoctorResult(
            "git-state",
            WARNING,
            "git executable was not found.",
            state=guardrail_doctor_models.MISSING,
        )

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
        hint = f" Hint: {item.hint}" if item.hint else ""
        print(f"{item.status} {item.name} [{item.state}]: {item.message}{hint}")


def status_code(results: list[DoctorResult], *, strict: bool) -> int:
    """Return the doctor process status for default or strict mode."""

    if any(item.status == ERROR for item in results):
        return 1
    if strict and any(item.status == WARNING for item in results):
        return 1
    return 0
