"""Local bootstrap and hook-install helpers for the guardrail kit."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from ai_guardrails.core.runtime import hardened_subprocess_env
from ai_guardrails.core.tool_capabilities import bootstrap_scope_note

MACOS_HIDDEN_FILE_FLAG = 0x8000


def bootstrap() -> int:
    """Bootstrap local tooling, install dependencies, install hooks."""

    repo_root = project_root()
    python_path = ensure_virtualenv(repo_root)
    if python_path is None:
        return 1

    dependency_status = install_dependencies(repo_root, python_path)
    if dependency_status != 0:
        return dependency_status

    return install()


def install() -> int:
    """Install local hooks without reinstalling dependencies."""

    repo_root = project_root()
    pre_commit_status = install_pre_commit(repo_root)
    report_codex_hooks(repo_root)
    return pre_commit_status


def project_root() -> Path:
    """Find the repository root command should operate on."""

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_project_root(candidate):
            return candidate

    package_path = Path(__file__).resolve()
    for candidate in package_path.parents:
        if is_project_root(candidate):
            return candidate
    return cwd


def is_project_root(candidate: Path) -> bool:
    """Return whether path looks like a guardrail-managed repository root."""

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
    """Install development dependencies from the preferred manifest."""

    dependency_file = preferred_dependency_file(repo_root)
    if not dependency_file.exists():
        print(
            "FAIL bootstrap: config/dev-lock.txt or config/dev-dependencies.txt not present.",
            file=sys.stderr,
        )
        return 1

    dependency_path = dependency_file.relative_to(repo_root)
    print(f"Installing Python package guardrail tools from {dependency_path}.", flush=True)
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
    """Install this project editable when package metadata exists."""

    if not (repo_root / "pyproject.toml").exists():
        return 0
    print("Installing ai_guardrails package editable.", flush=True)
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

    source_package = repo_root / "src" / "ai_guardrails"
    if not source_package.is_dir():
        return

    for site_packages in site_package_paths(repo_root, python_path):
        package_link = site_packages / "ai_guardrails"
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


def report_codex_hooks(repo_root: Path) -> None:
    """Print whether repo-local Codex hook configuration exists."""

    config_path = repo_root / ".codex" / "config.toml"
    if config_path.exists():
        print("Codex hooks configured in .codex/config.toml.")
