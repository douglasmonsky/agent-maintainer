"""Tests for package metadata and public command surface."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
import tomllib

from packaging.requirements import Requirement

from tests.support.paths import REPO_ROOT

SOURCE_METADATA = REPO_ROOT / "src" / "agent_maintainer.egg-info"


def cleanup_source_metadata() -> None:
    """Remove editable-install metadata generated during packaging tests."""
    shutil.rmtree(SOURCE_METADATA, ignore_errors=True)


def test_project_metadata_uses_agent_maintainer_identity() -> None:
    """Package metadata exposes the renamed distribution and console command."""

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    assert metadata["project"]["name"] == "agent-maintainer"
    assert metadata["project"]["version"] == "0.1.0b7"
    assert metadata["project"]["description"] == (
        "Repository maintenance checks and diagnostics for AI-assisted Python development."
    )
    assert metadata["project"]["scripts"] == {
        "agent-maintainer": "agent_maintainer.cli:console_main",
        "archguard": "archguard.cli:console_main",
        "docsync": "docsync.cli:console_main",
    }
    assert metadata["build-system"]["requires"] == ["setuptools>=77", "wheel"]
    assert metadata["project"]["license"] == "MIT"
    assert metadata["project"]["license-files"] == ["LICENSE"]
    assert metadata["project"]["authors"] == [{"name": "Doug Monsky"}]
    assert metadata["project"]["urls"]["Repository"] == (
        "https://github.com/douglasmonsky/agent-maintainer"
    )
    assert metadata["project"]["urls"]["Documentation"] == (
        "https://github.com/douglasmonsky/agent-maintainer#readme"
    )
    assert "License :: OSI Approved :: MIT License" not in metadata["project"]["classifiers"]
    assert "Programming Language :: Python :: 3.14" in metadata["project"]["classifiers"]
    assert {"core", "agent", "hardening", "manual", "compression", "mcp", "all"} <= set(
        metadata["project"]["optional-dependencies"]
    )


def test_setup_skill_resources_are_declared_as_package_data() -> None:
    """Built distributions retain both portable setup skill resources."""

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    assert metadata["tool"]["setuptools"]["package-data"] == {
        "agent_maintainer.skill": [
            "resources/agent-maintainer-setup/SKILL.md",
            "resources/agent-maintainer-setup/agents/openai.yaml",
        ]
    }


def test_optional_dependency_extras_are_flattened() -> None:
    """Extras avoid recursive self-references so installers stay predictable."""

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    extras = metadata["project"]["optional-dependencies"]
    for dependencies in extras.values():
        assert len(dependencies) == len(set(dependencies))
        assert all(not dependency.startswith("agent-maintainer[") for dependency in dependencies)

    assert set(extras["core"]) <= set(extras["agent"])
    assert set(extras["core"]) <= set(extras["hardening"])
    assert set(extras["core"]) <= set(extras["all"])
    assert set(extras["manual"]) <= set(extras["all"])
    assert set(extras["hardening"]) <= set(extras["all"])
    assert extras["compression"] == ["headroom-ai"]
    assert extras["mcp"] == ["mcp>=1.0"]
    assert "headroom-ai" not in extras["all"]
    assert "mcp>=1.0" in extras["all"]
    assert all("hypothesis" not in dependencies for dependencies in extras.values())
    assert all("rust-just" not in dependencies for dependencies in extras.values())
    assert "semgrep>=1.169.0" in extras["manual"]
    assert "semgrep>=1.169.0" in extras["all"]


def test_package_extras_have_valid_requirement_strings() -> None:
    """Declared extras parse without network or clean install state."""

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    extras = metadata["project"]["optional-dependencies"]
    for dependencies in extras.values():
        for dependency in dependencies:
            Requirement(dependency)


def test_package_module_entrypoint_help() -> None:
    """The module entrypoint works without relying on console PATH state."""

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "agent_maintainer", "--help"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "python -m agent_maintainer verify --profile precommit" in result.stdout


def test_archguard_module_entrypoint_help() -> None:
    """The Archguard entrypoint works without relying on console PATH state."""

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "archguard", "--help"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "tach-config" in result.stdout
