"""Smoke tests for package-first downstream onboarding."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
from pathlib import Path

from tests.support.paths import REPO_ROOT


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run a command and include output in assertion failures."""

    result = subprocess.run(  # nosec B603
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def write_downstream_repo(repo: Path) -> None:
    """Create a minimal package with tests."""

    (repo / "src" / "example_pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "example_pkg" / "__init__.py").write_text(
        '"""Example package for Agent Maintainer onboarding smoke tests."""\n\n'
        "\n"
        "def add(left: int, right: int) -> int:\n"
        '    """Return the sum of two integers."""\n'
        "    return left + right\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_smoke.py").write_text(
        "from example_pkg import add\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )


def test_core_initializer_supports_clean_downstream_precommit(tmp_path: Path) -> None:
    """A new repo initialized with core files can run the precommit profile."""

    repo = tmp_path / "downstream"
    repo.mkdir()
    write_downstream_repo(repo)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run(
        [
            sys.executable,
            "-m",
            "agent_maintainer",
            "init",
            "--track",
            "core",
            "--target",
            str(repo),
        ],
        cwd=REPO_ROOT,
        env=env,
    )

    starter_config = (repo / "config" / "pyproject.agent-maintainer.toml").read_text(
        encoding="utf-8"
    )
    (repo / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["setuptools>=69", "wheel"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[project]\n"
        'name = "example-pkg"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n\n'
        "[tool.setuptools.packages.find]\n"
        'where = ["src"]\n\n'
        "[tool.pytest.ini_options]\n"
        'pythonpath = ["src"]\n\n' + starter_config,
        encoding="utf-8",
    )

    run(["git", "init", "-b", "main"], cwd=repo)
    run(["git", "add", "pyproject.toml", "src", "tests", "config"], cwd=repo)
    run(
        [
            "git",
            "-c",
            "user.email=agent-maintainer@example.invalid",
            "-c",
            "user.name=Agent Maintainer",
            "commit",
            "-m",
            "test: add downstream smoke package",
        ],
        cwd=repo,
    )

    run(
        [
            sys.executable,
            "-m",
            "agent_maintainer",
            "verify",
            "--profile",
            "precommit",
            "--base-ref",
            "HEAD",
        ],
        cwd=repo,
        env=env,
    )
