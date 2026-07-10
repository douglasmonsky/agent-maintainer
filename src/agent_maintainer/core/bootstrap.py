"""Local bootstrap and hook-install helpers for the Agent Maintainer."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from agent_maintainer.core import setup_plans
from agent_maintainer.core.runtime import hardened_subprocess_env
from agent_maintainer.core.tooling.capabilities import bootstrap_scope_note
from agent_maintainer.hooks.manager import (
    ALL_CLIENTS,
    REPO_SCOPE,
    InstallOptions,
    install_hooks,
    status_hooks,
)

MACOS_HIDDEN_FILE_FLAG = 0x8000


def bootstrap(*, target: Path | None = None, dry_run: bool = False) -> int:
    """Bootstrap local tooling and dependencies without installing hooks."""

    repo_root = setup_plans.selected_root(target, discovered=project_root())
    if dry_run:
        setup_plans.print_bootstrap_plan(
            repo_root,
            preferred_dependency_file(repo_root),
            local_source=has_local_agent_maintainer_source(repo_root),
        )
        return 0
    python_path = ensure_virtualenv(repo_root)
    if python_path is None:
        return 1

    return install_dependencies(repo_root, python_path)


def install(
    *,
    target: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Install local hooks without reinstalling dependencies."""

    repo_root = setup_plans.selected_root(target, discovered=project_root())
    pre_commit_status = (
        setup_plans.preview_pre_commit(repo_root) if dry_run else install_pre_commit(repo_root)
    )
    hooks_status = install_hooks(
        InstallOptions(
            target=repo_root,
            client=ALL_CLIENTS,
            scope=REPO_SCOPE,
            dry_run=dry_run,
            force=force,
        )
    )
    if not dry_run:
        report_agent_hooks(repo_root)
    if pre_commit_status != 0:
        return pre_commit_status
    return hooks_status


def project_root() -> Path:
    """Return repository root to operate on."""

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_project_root(candidate):
            return candidate
    return cwd


def is_project_root(candidate: Path) -> bool:
    """Return whether path looks like a maintainer-managed repository root."""

    return (candidate / "pyproject.toml").exists() or (candidate / ".git").exists()


def ensure_virtualenv(repo_root: Path) -> Path | None:
    """Return project virtualenv interpreter, creating ``.venv`` when needed."""

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
        env=hardened_subprocess_env(),
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return virtualenv_python


def install_dependencies(repo_root: Path, python_path: Path) -> int:
    """Install development dependencies from preferred manifest."""

    dependency_file = preferred_dependency_file(repo_root)
    if not dependency_file.exists():
        if not has_local_agent_maintainer_source(repo_root):
            print(
                "SKIP bootstrap: config/dev-lock.txt or config/dev-dependencies.txt "
                "not present; leaving consumer repository dependencies unchanged.",
                flush=True,
            )
            return install_editable_package(repo_root, python_path)
        print(
            "FAIL bootstrap: config/dev-lock.txt or config/dev-dependencies.txt not present.",
            file=sys.stderr,
        )
        return 1

    dependency_path = dependency_file.relative_to(repo_root)
    print(f"Installing Python package Agent Maintainer tools from {dependency_path}.", flush=True)
    result = subprocess.run(  # nosec B603
        [str(python_path), "-m", "pip", "install", "-r", str(dependency_path)],
        cwd=repo_root,
        env=hardened_subprocess_env(),
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return result.returncode
    repair_pth_visibility(repo_root, python_path)
    editable_status = install_editable_package(repo_root, python_path)
    if editable_status == 0:
        print(bootstrap_scope_note(), flush=True)
    return editable_status


def install_editable_package(repo_root: Path, python_path: Path) -> int:
    """Install local Agent Maintainer source checkout when present."""

    if not has_local_agent_maintainer_source(repo_root):
        return 0
    print("Installing agent_maintainer package editable.", flush=True)
    result = subprocess.run(  # nosec B603
        [str(python_path), "-m", "pip", "install", "-e", ".", "--no-deps"],
        cwd=repo_root,
        env=hardened_subprocess_env(),
        text=True,
        check=False,
    )
    if result.returncode == 0:
        repair_pth_visibility(repo_root, python_path)
        ensure_editable_package_link(repo_root, python_path)
    return result.returncode


def has_local_agent_maintainer_source(repo_root: Path) -> bool:
    """Return whether repo root contains this package source checkout."""

    return (repo_root / "src" / "agent_maintainer" / "__init__.py").exists()


def repair_pth_visibility(repo_root: Path, python_path: Path) -> None:
    """Clear macOS hidden flags from installed ``.pth`` files when present."""

    hidden_flag = hidden_file_flag()
    if hidden_flag is None:
        return

    for site_packages in site_package_paths(repo_root, python_path):
        for pth_file in site_packages.glob("*.pth"):
            clear_hidden_file_flag(pth_file, hidden_flag)


def ensure_editable_package_link(repo_root: Path, python_path: Path) -> None:
    """Create local source-package symlink when editable ``.pth`` is unreliable."""

    source_package = repo_root / "src" / "agent_maintainer"
    if not source_package.is_dir():
        return

    for site_packages in site_package_paths(repo_root, python_path):
        package_link = site_packages / "agent_maintainer"
        if package_link.is_symlink():
            if package_link.resolve() == source_package:
                return
            package_link.unlink()
        if package_link.exists():
            return
        try:
            package_link.symlink_to(source_package, target_is_directory=True)
        except OSError:
            return
        return


def site_package_paths(repo_root: Path, python_path: Path) -> tuple[Path, ...]:
    """Return site-package directories reported by target Python interpreter."""

    result = subprocess.run(  # nosec B603
        [
            str(python_path),
            "-c",
            r"import site; print('\n'.join(site.getsitepackages()))",
        ],
        cwd=repo_root,
        env=hardened_subprocess_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ()
    return tuple(Path(line) for line in result.stdout.splitlines() if line)


def hidden_file_flag() -> int | None:
    """Return platform hidden-file flag when Python can clear it."""

    if chflags_command() is None:
        return None
    return MACOS_HIDDEN_FILE_FLAG


def chflags_command() -> str | None:
    """Return local chflags command when this platform provides it."""

    return shutil.which("chflags")


def clear_hidden_file_flag(path: Path, hidden_flag: int) -> None:
    """Clear hidden flag from one file, ignoring unsupported filesystem states."""

    command = chflags_command()
    if command is None:
        return
    try:
        current_flags = getattr(path.stat(), "st_flags", 0)
    except OSError:
        return
    if not current_flags & hidden_flag:
        return
    subprocess.run(  # nosec B603
        [command, "nohidden", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )


def preferred_dependency_file(repo_root: Path) -> Path:
    """Choose the pinned dev lock when present, otherwise the editable input."""

    lock_file = repo_root / "config" / "dev-lock.txt"
    if lock_file.exists():
        return lock_file
    return repo_root / "config" / "dev-dependencies.txt"


def install_pre_commit(repo_root: Path) -> int:
    """Install pre-commit hook when repository configured it."""

    config_path = repo_root / ".pre-commit-config.yaml"
    if not config_path.exists():
        print("SKIP pre-commit: .pre-commit-config.yaml not present.")
        return 0

    pre_commit = find_pre_commit(repo_root)
    if pre_commit is None:
        print("FAIL pre-commit: command not found. Install config/dev-dependencies.txt first.")
        return 1

    result = subprocess.run(  # nosec B603
        [pre_commit, "install"],
        cwd=repo_root,
        env=hardened_subprocess_env(),
        text=True,
        check=False,
    )
    return result.returncode


def find_pre_commit(repo_root: Path) -> str | None:
    """Find pre-commit in local virtualenv or on ``PATH``."""

    for relative in (".venv/bin/pre-commit", "venv/bin/pre-commit"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return shutil.which("pre-commit")


def report_agent_hooks(repo_root: Path) -> None:
    """Print whether repo-local agent hook configuration exists."""

    status_hooks(repo_root, ALL_CLIENTS, REPO_SCOPE)


def report_codex_hooks(repo_root: Path) -> None:
    """Print whether repo-local Codex hook configuration exists."""

    report_agent_hooks(repo_root)
