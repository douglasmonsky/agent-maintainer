"""Smoke tests for package-first downstream onboarding."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import pytest

from tests.support.paths import REPO_ROOT


@dataclass(frozen=True)
class DownstreamLayout:
    """Minimal downstream package layout to verify."""

    name: str
    package_root: str
    package_add_path: str
    package_finder: str
    pytest_pythonpath: str
    source_roots: tuple[str, ...]
    package_paths: tuple[str, ...]
    coverage_source: tuple[str, ...]
    file_length_paths: tuple[str, ...]
    structure_paths: tuple[str, ...]
    vulture_paths: tuple[str, ...]


SRC_LAYOUT = DownstreamLayout(
    name="src-layout",
    package_root="src",
    package_add_path="src",
    package_finder='[tool.setuptools.packages.find]\nwhere = ["src"]\n',
    pytest_pythonpath="src",
    source_roots=("src",),
    package_paths=("src",),
    coverage_source=("src",),
    file_length_paths=("src", "tests"),
    structure_paths=("src",),
    vulture_paths=("src", "tests"),
)
FLAT_LAYOUT = DownstreamLayout(
    name="flat-layout",
    package_root=".",
    package_add_path="example_pkg",
    package_finder='[tool.setuptools.packages.find]\ninclude = ["example_pkg*"]\n',
    pytest_pythonpath=".",
    source_roots=("example_pkg",),
    package_paths=("example_pkg",),
    coverage_source=("example_pkg",),
    file_length_paths=("example_pkg", "tests"),
    structure_paths=("example_pkg",),
    vulture_paths=("example_pkg", "tests"),
)


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


def tuple_toml(values: tuple[str, ...]) -> str:
    """Render a simple tuple of strings as TOML array syntax."""

    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def test_packaged_setup_skill_resources_and_help(tmp_path: Path) -> None:
    """Package data and its repository-independent command ship together."""
    skill_root = resources.files("agent_maintainer.skill").joinpath(
        "resources",
        "agent-maintainer-setup",
    )
    assert skill_root.joinpath("SKILL.md").is_file()
    assert skill_root.joinpath("agents", "openai.yaml").is_file()

    environment = dict(os.environ)
    environment.update(
        {
            "HOME": str(tmp_path / "home"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
    )
    run(
        [sys.executable, "-m", "agent_maintainer", "skill", "--help"],
        cwd=tmp_path,
        env=environment,
    )


def configured_starter_config(starter_config: str, layout: DownstreamLayout) -> str:
    """Return starter config adapted to a downstream layout."""

    replacements = {
        'source_roots = ["src"]': f"source_roots = {tuple_toml(layout.source_roots)}",
        'package_paths = ["src"]': f"package_paths = {tuple_toml(layout.package_paths)}",
        'coverage_source = ["src"]': f"coverage_source = {tuple_toml(layout.coverage_source)}",
        'file_length_paths = ["src", "tests", ".codex/hooks", ".claude/hooks"]': (
            f"file_length_paths = {tuple_toml(layout.file_length_paths)}"
        ),
        'structure_paths = ["src"]': f"structure_paths = {tuple_toml(layout.structure_paths)}",
        'vulture_paths = ["src", "tests", ".codex/hooks", ".claude/hooks"]': (
            f"vulture_paths = {tuple_toml(layout.vulture_paths)}"
        ),
    }
    configured = starter_config
    for old, new in replacements.items():
        configured = configured.replace(old, new)
    return configured


def write_downstream_repo(repo: Path, layout: DownstreamLayout) -> None:
    """Write a minimal package and tests for the selected layout."""

    package_dir = repo / layout.package_root / "example_pkg"
    package_dir.mkdir(parents=True)
    (repo / "tests").mkdir()
    (package_dir / "__init__.py").write_text(
        '"""Example package for Agent Maintainer onboarding smoke tests."""\n\n\n'
        "def add(left: int, right: int) -> int:\n"
        '    """Return the sum of two integers."""\n'
        "    return left + right\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_smoke.py").write_text(
        "from example_pkg import add\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )


def write_pyproject(repo: Path, layout: DownstreamLayout, starter_config: str) -> None:
    """Write downstream package metadata plus configured Agent Maintainer config."""

    (repo / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["setuptools>=69", "wheel"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[project]\n"
        'name = "example-pkg"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n\n'
        f"{layout.package_finder}\n"
        "[tool.pytest.ini_options]\n"
        f'pythonpath = ["{layout.pytest_pythonpath}"]\n\n'
        + configured_starter_config(starter_config, layout),
        encoding="utf-8",
    )


@pytest.mark.parametrize("layout", [SRC_LAYOUT, FLAT_LAYOUT], ids=lambda layout: layout.name)
def test_core_initializer_supports_clean_downstream_precommit(
    tmp_path: Path,
    layout: DownstreamLayout,
) -> None:
    """Core init supports common downstream package layouts."""

    repo = tmp_path / layout.name
    repo.mkdir()
    write_downstream_repo(repo, layout)
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
        encoding="utf-8",
    )
    write_pyproject(repo, layout, starter_config)

    run(["git", "init", "-b", "main"], cwd=repo)
    run(["git", "add", "pyproject.toml", layout.package_add_path, "tests", "config"], cwd=repo)
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
