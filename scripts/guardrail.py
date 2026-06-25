#!/usr/bin/env python3
"""Canonical command-line entrypoint for repository guardrails."""
# pylint: disable=wrong-import-position

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.guardrail_doctor import main as doctor_main
from scripts.verify_quiet import main as verify_main

USAGE = """Usage:
  python -m scripts.guardrail bootstrap
  python -m scripts.guardrail doctor [doctor options]
  python -m scripts.guardrail install
  python -m scripts.guardrail verify [verify options]

Examples:
  python -m scripts.guardrail bootstrap
  python -m scripts.guardrail doctor --strict
  python -m scripts.guardrail install
  python -m scripts.guardrail verify --profile fast
  python -m scripts.guardrail verify --profile precommit
  python -m scripts.guardrail verify --profile full
"""


def main(argv: list[str]) -> int:
    """Dispatch the top-level guardrail command line."""

    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE.rstrip())
        status = 0
    else:
        command, *command_args = argv
        status = route_command(command, command_args)
    return status


def route_command(command: str, command_args: list[str]) -> int:
    """Route one guardrail subcommand to its implementation."""

    if command == "bootstrap":
        status = bootstrap()
    elif command == "doctor":
        status = doctor_main(command_args)
    elif command == "install":
        status = install()
    elif command == "verify":
        status = verify_main(command_args)
    else:
        print(f"Unknown guardrail command: {command}", file=sys.stderr)
        print(USAGE.rstrip(), file=sys.stderr)
        status = 2
    return status


def bootstrap() -> int:
    """Create local tooling, install dependencies, and install hooks."""

    repo_root = Path(__file__).resolve().parents[1]
    python_path = ensure_virtualenv(repo_root)
    if python_path is None:
        return 1

    dependency_status = install_dependencies(repo_root, python_path)
    if dependency_status != 0:
        return dependency_status

    return install()


def install() -> int:
    """Install local hooks without reinstalling dependencies."""

    repo_root = Path(__file__).resolve().parents[1]
    pre_commit_status = install_pre_commit(repo_root)
    report_codex_hooks(repo_root)
    return pre_commit_status


def ensure_virtualenv(repo_root: Path) -> Path | None:
    """Return a project virtualenv interpreter, creating .venv when needed."""

    virtualenv_python = repo_root / ".venv" / "bin" / "python"
    if virtualenv_python.exists():
        return virtualenv_python

    system_python = shutil.which("python3") or shutil.which("python")
    if system_python is None:
        print("FAIL bootstrap: python3 command not found.", file=sys.stderr)
        return None

    print("Creating .venv with the active Python interpreter.", flush=True)
    result = subprocess.run(  # nosec B603
        [system_python, "-m", "venv", ".venv"],
        cwd=repo_root,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    return virtualenv_python


def install_dependencies(repo_root: Path, python_path: Path) -> int:
    """Install development dependencies from the preferred manifest."""

    dependency_file = preferred_dependency_file(repo_root)
    if not dependency_file.exists():
        print(
            "FAIL bootstrap: config/dev-lock.txt or config/dev-dependencies.txt is not present.",
            file=sys.stderr,
        )
        return 1

    dependency_path = dependency_file.relative_to(repo_root)
    print(f"Installing dev dependencies from {dependency_path}.", flush=True)
    result = subprocess.run(  # nosec B603
        [str(python_path), "-m", "pip", "install", "-r", str(dependency_path)],
        cwd=repo_root,
        text=True,
        check=False,
    )
    return result.returncode


def preferred_dependency_file(repo_root: Path) -> Path:
    """Choose the pinned dev lock when present, otherwise the editable input."""

    lock_file = repo_root / "config" / "dev-lock.txt"
    if lock_file.exists():
        return lock_file
    return repo_root / "config" / "dev-dependencies.txt"


def install_pre_commit(repo_root: Path) -> int:
    """Install the pre-commit hook when the repository is configured for it."""

    config_path = repo_root / ".pre-commit-config.yaml"
    if not config_path.exists():
        print("SKIP pre-commit: .pre-commit-config.yaml is not present.")
        return 0

    pre_commit = find_pre_commit(repo_root)
    if pre_commit is None:
        print("FAIL pre-commit: command not found. Install config/dev-dependencies.txt first.")
        return 1

    result = subprocess.run(  # nosec B603
        [pre_commit, "install"],
        cwd=repo_root,
        text=True,
        check=False,
    )
    return result.returncode


def find_pre_commit(repo_root: Path) -> str | None:
    """Find pre-commit in a local virtualenv or on PATH."""

    for relative in (".venv/bin/pre-commit", "venv/bin/pre-commit"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return shutil.which("pre-commit")


def report_codex_hooks(repo_root: Path) -> None:
    """Print whether repo-local Codex hook configuration exists."""

    config_path = repo_root / ".codex" / "config.toml"
    if config_path.exists():
        print("Codex hooks are configured in .codex/config.toml.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
