"""Hash repository and environment inputs used for verifier result reuse."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Mapping
from pathlib import Path

CONFIG_FINGERPRINT_PATHS = (
    "pyproject.toml",
    "tach.toml",
    ".pre-commit-config.yaml",
    ".github/dependabot.yml",
    ".github/workflows/verify.yml",
    "semgrep.yml",
    "osv-scanner.toml",
    "config/dev-dependencies.txt",
    "config/dev-lock.txt",
    "package.json",
    "package-lock.json",
)
ENVIRONMENT_FINGERPRINT_NAMES = frozenset(("PATH", "PYTHONPATH", "VIRTUAL_ENV"))
ENVIRONMENT_FINGERPRINT_PREFIX = "AGENT_MAINTAINER_"


def git_hash(repo_root: Path, *args: str) -> str:
    """Return stable hash for Git command output."""

    output = git_output(repo_root, *args)
    return hashlib.sha256(output.encode()).hexdigest()


def git_output(repo_root: Path, *args: str) -> str:
    """Return Git stdout or an empty string when Git is unavailable."""

    git_path = shutil.which("git")
    if git_path is None:
        return ""
    result = subprocess.run(  # nosec B603
        [git_path, *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def file_hash(path: Path) -> str:
    """Return stable hash for one file."""

    try:
        content = path.read_bytes()
    except OSError:
        content = b""
    return hashlib.sha256(content).hexdigest()


def files_hash(repo_root: Path, paths: tuple[str, ...]) -> str:
    """Return stable hash of verifier-relevant config files."""

    digest = hashlib.sha256()
    for relative_path in paths:
        path = repo_root / relative_path
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(file_hash(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def environment_hash(environ: Mapping[str, str]) -> str:
    """Return stable identity for Python and verifier-affecting environment state."""

    selected = {
        key: value
        for key, value in environ.items()
        if key in ENVIRONMENT_FINGERPRINT_NAMES or key.startswith(ENVIRONMENT_FINGERPRINT_PREFIX)
    }
    payload = {
        "environment": selected,
        "python_executable": sys.executable,
        "python_version": sys.version,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def untracked_files_hash(repo_root: Path) -> str:
    """Return stable hash of untracked, non-ignored repository files."""

    relative_paths = sorted(
        path
        for path in git_output(
            repo_root,
            "ls-files",
            "--others",
            "--exclude-standard",
        ).splitlines()
        if path
    )
    digest = hashlib.sha256()
    for relative_path in relative_paths:
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(file_hash(repo_root / relative_path).encode())
        digest.update(b"\0")
    return digest.hexdigest()
