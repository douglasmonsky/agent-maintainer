"""Setup and health diagnostics for the Agent Maintainer."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

from agent_maintainer.core import config as maintainer_config
from agent_maintainer.doctor import setup as maintainer_doctor_setup
from agent_maintainer.doctor.support import hook_audit as maintainer_doctor_hook_audit
from agent_maintainer.doctor.support import logs as maintainer_doctor_logs
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.doctor.support import policy as maintainer_doctor_policy

DoctorResult = maintainer_doctor_models.DoctorResult
ERROR = maintainer_doctor_models.ERROR
OK = maintainer_doctor_models.OK
WARNING = maintainer_doctor_models.WARNING

check_python_version = maintainer_doctor_setup.check_python_version
check_agent_guidance = maintainer_doctor_setup.check_agent_guidance
check_layout = maintainer_doctor_setup.check_layout
check_optional_gates = maintainer_doctor_setup.check_optional_gates
check_tests = maintainer_doctor_setup.check_tests
check_tool_capabilities = maintainer_doctor_setup.check_tool_capabilities


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
    results = run_doctor(Path.cwd(), maintainer_config.load_config())
    if args.json:
        print(json.dumps([item.__dict__ for item in results], indent=2))
    else:
        print_text(results)
    return status_code(results, strict=args.strict)


def run_doctor(repo_root: Path, config: maintainer_config.MaintainerConfig) -> list[DoctorResult]:
    """Run every setup diagnostic against a repository root."""

    return [
        check_python_version(),
        check_repo_root(repo_root),
        check_virtualenv(repo_root),
        check_tool_capabilities(repo_root, config),
        maintainer_doctor_setup.check_architecture_backend(repo_root, config),
        check_layout(config),
        check_tests(repo_root, config),
        maintainer_doctor_setup.check_thresholds(config),
        maintainer_doctor_setup.check_structure_thresholds(config),
        maintainer_doctor_policy.check_pyright_config(repo_root, config),
        check_pre_commit(repo_root),
        check_codex_hooks(repo_root),
        check_claude_code_hooks(repo_root),
        maintainer_doctor_hook_audit.check_hook_audit(repo_root, config),
        maintainer_doctor_policy.check_pip_audit_safety(config),
        maintainer_doctor_policy.check_secret_scanning_policy(config),
        maintainer_doctor_policy.check_context_pack_upload_policy(repo_root, config),
        check_optional_gates(repo_root, config),
        check_canonical_commands(repo_root),
        check_agent_guidance(repo_root, config),
        check_git_state(repo_root),
        maintainer_doctor_logs.check_recent_logs(repo_root, config),
    ]


def check_repo_root(repo_root: Path) -> DoctorResult:
    """Check for files that identify a usable maintainer repository root."""

    missing = [
        path
        for path in (".git", "src/agent_maintainer/__main__.py")
        if not (repo_root / path).exists()
    ]
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "repo-root",
            ERROR,
            f"Missing required repo paths: {missing_paths}",
            state=maintainer_doctor_models.MISSING,
        )
    if not (repo_root / "pyproject.toml").exists():
        return DoctorResult(
            "repo-root",
            WARNING,
            "pyproject.toml is absent; defaults will be used.",
            state=maintainer_doctor_models.MISSING,
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
        state=maintainer_doctor_models.MISSING,
        hint="Run python3 -m agent_maintainer bootstrap.",
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
            state=maintainer_doctor_models.NOT_APPLICABLE,
        )
    if not hook_path.exists():
        return DoctorResult(
            "pre-commit-hook",
            WARNING,
            "pre-commit hook is not installed.",
            state=maintainer_doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer install.",
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
            state=maintainer_doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer install.",
        )
    text = config_path.read_text(encoding="utf-8")
    if "hooks = true" not in text:
        return DoctorResult(
            "codex-hooks",
            WARNING,
            ".codex/config.toml does not enable hooks.",
            state=maintainer_doctor_models.DISABLED,
            hint=(
                "Set hooks = true for this repo if Codex hooks should enforce "
                "Agent Maintainer checks."
            ),
        )
    return DoctorResult("codex-hooks", OK, ".codex/config.toml enables hooks.")


def check_claude_code_hooks(repo_root: Path) -> DoctorResult:
    """Report repo-local Claude Code hooks configured."""

    settings_path = repo_root / ".claude" / "settings.json"
    hook_paths = (
        repo_root / ".claude" / "hooks" / "post_tool_use.py",
        repo_root / ".claude" / "hooks" / "stop.py",
        repo_root / ".claude" / "hooks" / "subagent_stop.py",
    )
    if not settings_path.exists():
        return DoctorResult(
            "claude-code-hooks",
            WARNING,
            ".claude/settings.json absent.",
            state=maintainer_doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer hooks install claude-code.",
        )
    missing = [path.relative_to(repo_root).as_posix() for path in hook_paths if not path.exists()]
    if missing:
        missing_files = ", ".join(missing)
        return DoctorResult(
            "claude-code-hooks",
            WARNING,
            f"Claude Code hook scripts missing: {missing_files}.",
            state=maintainer_doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer hooks install claude-code.",
        )
    text = settings_path.read_text(encoding="utf-8")
    settings_markers = ("agent_maintainer", "agent-maintainer hooks run", ".claude/hooks")
    if not any(marker in text for marker in settings_markers):
        return DoctorResult(
            "claude-code-hooks",
            WARNING,
            ".claude/settings.json does not reference Agent Maintainer hooks.",
            state=maintainer_doctor_models.DISABLED,
            hint="Run python3 -m agent_maintainer hooks install claude-code.",
        )
    return DoctorResult(
        "claude-code-hooks",
        OK,
        ".claude/settings.json enables Agent Maintainer hooks.",
    )


def check_canonical_commands(repo_root: Path) -> DoctorResult:
    """Check that CI, pre-commit, and hooks use the module entrypoint."""

    expectations = {
        ".github/workflows/verify.yml": "python3 -m agent_maintainer verify",
        ".pre-commit-config.yaml": "python3 -m agent_maintainer verify --profile precommit",
        ".codex/hooks/post_edit_fast_gate.py": "agent_maintainer",
        ".codex/hooks/stop_full_verify.py": "agent_maintainer",
        ".claude/settings.json": ".claude/hooks",
        ".claude/hooks/post_tool_use.py": "agent_maintainer",
        ".claude/hooks/stop.py": "agent_maintainer",
        ".claude/hooks/subagent_stop.py": "agent_maintainer",
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
            state=maintainer_doctor_models.UNSAFE_CONFIG,
            hint="Use python3 -m agent_maintainer in CI, pre-commit, and Codex hooks.",
        )
    if missing:
        missing_paths = ", ".join(missing)
        return DoctorResult(
            "canonical-commands",
            WARNING,
            f"Missing command files: {missing_paths}",
            state=maintainer_doctor_models.MISSING,
            hint="Run python3 -m agent_maintainer install or add the missing integration files.",
        )
    return DoctorResult(
        "canonical-commands",
        OK,
        "CI, pre-commit, and agent hooks use module entrypoint.",
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
            state=maintainer_doctor_models.MISSING,
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
