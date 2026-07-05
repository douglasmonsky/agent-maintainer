"""Downstream install contract for agent-task-broker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import sysconfig
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = ROOT / "experiments" / "agent-task-broker"


def test_downstream_install_and_cli_contract(tmp_path: Path) -> None:
    """Install Agent Maintainer wheel then exercise broker CLI downstream."""
    venv_path = tmp_path / "venv"
    dist_dir = tmp_path / "dist"
    repo = tmp_path / "repo"
    repo.mkdir()

    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(venv_path)
    python = venv_python(venv_path)
    broker = venv_bin(venv_path, "agent-task-broker")

    run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
            str(ROOT),
        ],
    )
    wheel = next(dist_dir.glob("agent_maintainer-*.whl"))
    run([python, "-m", "pip", "install", "--no-deps", str(wheel)])
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "--no-deps",
            "-e",
            str(EXPERIMENT),
        ],
        env=build_backend_env(),
    )
    version = run(
        [
            python,
            "-c",
            (
                "from agent_task_broker.cli import installed_agent_maintainer_version; "
                "print(installed_agent_maintainer_version())"
            ),
        ]
    )
    assert version.stdout.strip() == agent_maintainer_version()
    assert "usage: agent-task-broker" in run([broker, "--help"]).stdout
    assert "usage: agent-task-broker" in run([python, "-m", "agent_task_broker", "--help"]).stdout

    run([broker, "--root", str(repo), "init"])
    add = run([broker, "--root", str(repo), "add", "Review focused task", "--priority", "5"])
    assert "task-0001 [open] p5 Review focused task" in add.stdout

    assert "task-0001 [open]" in run([broker, "--root", str(repo), "next"]).stdout
    assert (
        "CLAIMED task-0001 attempt task-0001-1"
        in run([broker, "--root", str(repo), "claim", "task-0001", "--agent", "codex"]).stdout
    )
    assert (
        "LOCKED lock-0001 task-0001 write path src/example.py"
        in run(
            [
                broker,
                "--root",
                str(repo),
                "lock",
                "claim",
                "task-0001",
                "--kind",
                "path",
                "--target",
                "src/example.py",
                "--mode",
                "write",
            ],
        ).stdout
    )
    assert (
        "lock-0001 task-0001 write path src/example.py"
        in run(
            [broker, "--root", str(repo), "locks"],
        ).stdout
    )
    assert (
        "task_id"
        in run([broker, "--root", str(repo), "handoff", "task-0001", "--format", "json"]).stdout
    )
    assert (
        "task/task-0001"
        in run(
            [broker, "--root", str(repo), "worktree", "plan", "task-0001", "--format", "json"],
        ).stdout
    )
    assert (
        "COMPLETED task-0001: Done"
        in run(
            [
                broker,
                "--root",
                str(repo),
                "complete",
                "task-0001",
                "--summary",
                "Done",
                "--verification",
                "pytest -q",
            ]
        ).stdout
    )
    run([broker, "--root", str(repo), "add", "Blocked task"])
    assert (
        "task-0002 [open] p0 Blocked task"
        in run([broker, "--root", str(repo), "list", "--status", "open"]).stdout
    )
    assert (
        "ABANDONED task-0002: blocked"
        in run([broker, "--root", str(repo), "give-up", "task-0002", "--reason", "blocked"]).stdout
    )

    board = json.loads((repo / ".agent-task-broker" / "board.json").read_text())
    task = json.loads((repo / ".agent-task-broker" / "tasks" / "task-0001.json").read_text())
    assert board["tasks"] == ["task-0001", "task-0002"]
    assert task["status"] == "done"
    assert (repo / ".agent-task-broker" / "attempts" / "task-0001-1.json").exists()
    assert (repo / ".agent-task-broker" / "results" / "task-0001.json").exists()
    assert (repo / ".agent-task-broker" / "results" / "task-0002.json").exists()


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run command and return completed process."""
    result = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        env={**(env or os.environ), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def venv_python(venv_path: Path) -> str:
    """Return venv Python executable."""
    return str(venv_bin(venv_path, "python"))


def venv_bin(venv_path: Path, name: str) -> Path:
    """Return venv executable path."""
    return venv_path / ("Scripts" if os.name == "nt" else "bin") / name


def agent_maintainer_version() -> str:
    """Return source checkout Agent Maintainer version."""
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(metadata["project"]["version"])


def build_backend_env() -> dict[str, str]:
    """Return environment that exposes current build backend to temp venvs."""

    env = dict(os.environ)
    env["PYTHONPATH"] = sysconfig.get_paths()["purelib"]
    return env
