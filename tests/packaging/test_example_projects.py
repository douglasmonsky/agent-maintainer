"""Tests for documented example project layouts."""

from __future__ import annotations

import os
import subprocess  # nosec B404: tests run fixed local commands.
import sys
import tomllib
from pathlib import Path
from typing import Any

from archguard.tach_config import tach_config_issues
from tests.support.paths import REPO_ROOT

EXAMPLES_ROOT = REPO_ROOT / "examples"
FRESH_STRICT_COVERAGE_FLOOR = 90
LEGACY_RATCHET_COVERAGE_FLOOR = 80


def run_example_tests(example_root: Path, package_root: str) -> None:
    """Run an example project's own tests with the checkout on PYTHONPATH."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        (
            str(REPO_ROOT / "src"),
            str(example_root / "src"),
        ),
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(  # nosec B603: command shape is fixed for examples.
        [sys.executable, "-m", "pytest", "-q"],
        cwd=example_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert package_root in result.stdout or "passed" in result.stdout


def load_example_config(example_name: str) -> dict[str, Any]:
    """Load an example pyproject file."""
    with (EXAMPLES_ROOT / example_name / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_fresh_strict_example_is_runnable_and_strict() -> None:
    """The fresh-strict example should be a valid strict starter repo."""
    example_root = EXAMPLES_ROOT / "fresh-strict"
    config = load_example_config("fresh-strict")["tool"]["agent_maintainer"]

    assert config["mode"] == "fresh-strict"
    assert config["architecture_tool"] == "tach"
    assert config["coverage_fail_under"] == FRESH_STRICT_COVERAGE_FLOOR
    assert tach_config_issues(example_root, require_strict_root=True) == []

    run_example_tests(example_root, "fresh_strict_example")


def test_legacy_ratchet_example_is_runnable_and_conservative() -> None:
    """The legacy-ratchet example should keep heavy gates opt-in."""
    example_root = EXAMPLES_ROOT / "legacy-ratchet"
    config = load_example_config("legacy-ratchet")["tool"]["agent_maintainer"]

    assert config["mode"] == "legacy-ratchet"
    assert config["architecture_tool"] == "import-linter"
    assert config["coverage_fail_under"] == LEGACY_RATCHET_COVERAGE_FLOOR
    assert config["enable_wemake"] is False
    assert config["enable_interrogate"] is False

    run_example_tests(example_root, "legacy_ratchet_example")
