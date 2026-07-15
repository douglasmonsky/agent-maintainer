"""Real-process owner workflow contract smoke tests."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from tests.support.paths import REPO_ROOT

ENCODING = "utf-8"


@pytest.mark.owner_contract
def test_failed_fast_verification_repairs_to_pass(tmp_path: Path) -> None:
    """A fresh local repository exposes a repair fact and then passes."""

    prepare_repository(tmp_path)
    source = tmp_path / "src" / "demo" / "__init__.py"
    source.write_text("import os\n", encoding=ENCODING)

    failed = run_verifier(tmp_path)

    assert failed.returncode == 1, failed.stdout + failed.stderr
    last_failure = tmp_path / ".verify-logs" / "LAST_FAILURE.md"
    assert last_failure.is_file()
    failure_text = last_failure.read_text(encoding=ENCODING)
    assert "ruff" in failure_text
    assert "F401" in failure_text

    source.write_text('VALUE = "repaired"\n', encoding=ENCODING)
    passed = run_verifier(tmp_path)

    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert passed.stdout.splitlines()[0] == "PASS"


def prepare_repository(repo_root: Path) -> None:
    """Create a committed repository with deterministic fast checks."""

    source = repo_root / "src" / "demo" / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text('VALUE = "baseline"\n', encoding=ENCODING)
    (repo_root / "pyproject.toml").write_text(
        """[tool.agent_maintainer]
mode = "legacy-ratchet"
source_roots = ["src"]
package_paths = ["src/demo"]
test_roots = ["tests"]
file_length_paths = ["src"]
structure_paths = ["src"]
require_tests = false
allow_source_without_test_change = true
diagnostic_artifacts_enabled = true
diagnostic_artifacts_dir = ".verify-logs"
""",
        encoding=ENCODING,
    )
    run_git(repo_root, "init", "-q", "-b", "main")
    run_git(repo_root, "add", "--", "pyproject.toml", "src/demo/__init__.py")
    run_git(
        repo_root,
        "-c",
        "user.name=Agent Maintainer Test",
        "-c",
        "user.email=agent-maintainer@example.invalid",
        "commit",
        "-q",
        "-m",
        "test fixture",
    )


def run_verifier(repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Run the public verifier in a foreground isolated environment."""

    return subprocess.run(  # nosec B603
        [
            sys.executable,
            "-m",
            "agent_maintainer",
            "verify",
            "--profile",
            "fast",
        ],
        cwd=repo_root,
        env=subprocess_environment(),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def subprocess_environment() -> dict[str, str]:
    """Return an environment isolated from the active Codex task."""

    environment = dict(os.environ)
    for name in tuple(environment):
        if (
            name.startswith("AGENT_MAINTAINER_")
            or name.startswith("CODEX_")
            or name.startswith("COV_CORE_")
            or name == "COVERAGE_PROCESS_START"
        ):
            environment.pop(name)
    environment["PYTHONPATH"] = str(REPO_ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT"] = "1"
    return environment


def run_git(repo_root: Path, *arguments: str) -> None:
    """Run one Git fixture command."""

    completed = subprocess.run(  # nosec B603
        ["git", *arguments],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
