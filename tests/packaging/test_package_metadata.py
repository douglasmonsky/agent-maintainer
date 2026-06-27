"""Tests for package metadata and public command surface."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import tomllib

from tests.support.paths import REPO_ROOT


def test_project_metadata_uses_agent_maintainer_identity() -> None:
    """Package metadata exposes the renamed distribution and console command."""

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)

    assert metadata["project"]["name"] == "agent-maintainer"
    assert metadata["project"]["description"] == (
        "Repository maintenance checks and diagnostics for AI-assisted Python development."
    )
    assert metadata["project"]["scripts"] == {
        "agent-maintainer": "agent_maintainer.cli:console_main"
    }
    assert {"core", "agent", "hardening", "manual", "all"} <= set(
        metadata["project"]["optional-dependencies"]
    )


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
