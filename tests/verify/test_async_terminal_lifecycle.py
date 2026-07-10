"""Integration coverage for detached verification after terminal closure."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent_maintainer.verify import async_state
from agent_maintainer.wait.verifier import VerifierWaitConfig, wait_for_verifier_run
from tests.support.paths import REPO_ROOT

pty = pytest.importorskip("pty", reason="pseudo-terminal lifecycle is POSIX-specific")

RUN_ID = "terminal-close"
PARENT_TIMEOUT_SECONDS = 15
VERIFIER_TIMEOUT_SECONDS = 30


def test_async_verifier_survives_closed_parent_terminal(tmp_path: Path) -> None:
    """A real detached verifier owns stdin and reports its actual PASS result."""

    prepare_minimal_repository(tmp_path)
    parent_script = write_terminal_parent(tmp_path)
    environment = subprocess_environment()
    master_fd, slave_fd = pty.openpty()
    parent = subprocess.Popen(  # nosec B603
        [sys.executable, str(parent_script), RUN_ID],
        cwd=tmp_path,
        env=environment,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave_fd)
    try:
        assert parent.wait(timeout=PARENT_TIMEOUT_SECONDS) == 0
    finally:
        os.close(master_fd)
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=PARENT_TIMEOUT_SECONDS)

    result = wait_for_verifier_run(
        VerifierWaitConfig(
            run_id=RUN_ID,
            log_dir=tmp_path / ".verify-logs",
            interval_seconds=1,
            timeout_seconds=VERIFIER_TIMEOUT_SECONDS,
        ),
    )
    assert result.exit_code == 0
    assert result.manifest is not None
    assert result.manifest.succeeded
    state = async_state.read_async_state(
        tmp_path / ".verify-logs" / "jobs" / f"{RUN_ID}.json",
    )
    assert state is not None
    assert state.status == async_state.JOB_STATUS_PASSED
    assert state.exit_code == 0
    stderr_path = Path(state.stderr_path)
    if not stderr_path.is_absolute():
        stderr_path = tmp_path / stderr_path
    stderr_text = stderr_path.read_text(encoding="utf-8")
    assert "Bad file descriptor" not in stderr_text
    assert "Fatal Python error" not in stderr_text


def prepare_minimal_repository(repo_root: Path) -> None:
    """Create a committed repository whose fast profile is deterministic."""

    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "pass_check.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text(
        """[tool.agent_maintainer]
mode = "legacy-ratchet"
source_roots = ["scripts"]
package_paths = ["scripts"]
test_roots = ["tests"]
file_length_paths = ["scripts"]
structure_paths = ["scripts"]
require_tests = false
allow_source_without_test_change = true
diagnostic_artifacts_enabled = true
diagnostic_artifacts_dir = ".verify-logs"
""",
        encoding="utf-8",
    )
    run_git(repo_root, "init", "-q")
    run_git(repo_root, "add", "--", "pyproject.toml", "scripts/pass_check.py")
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


def write_terminal_parent(repo_root: Path) -> Path:
    """Write a parent that loses fd 0 immediately before async launch."""

    path = repo_root / "terminal_parent.py"
    path.write_text(
        """import os
import sys

from agent_maintainer.verify.quiet import main

os.close(0)
raise SystemExit(
    main(["--profile", "fast", "--async", "--run-id", sys.argv[1]])
)
""",
        encoding="utf-8",
    )
    return path


def subprocess_environment() -> dict[str, str]:
    """Return isolated environment that imports this checkout's source."""

    environment = dict(os.environ)
    for name in tuple(environment):
        if _inherited_test_control(name):
            environment.pop(name)
    source_path = str(REPO_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (source_path, existing_pythonpath) if item
    )
    environment["AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT"] = "1"
    return environment


def _inherited_test_control(name: str) -> bool:
    return (
        name.startswith("AGENT_MAINTAINER_")
        or name.startswith("CODEX_")
        or name.startswith("COV_CORE_")
        or name == "COVERAGE_PROCESS_START"
    )


def run_git(repo_root: Path, *arguments: str) -> None:
    """Run one quiet Git command for the synthetic repository."""

    completed = subprocess.run(  # nosec B603
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, json.dumps(
        {"stdout": completed.stdout, "stderr": completed.stderr},
    )
