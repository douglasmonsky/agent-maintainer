"""CI-visible downstream contract for the task broker experiment."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_TEST = (
    ROOT / "experiments" / "agent-task-broker" / "tests" / "test_downstream_install_contract.py"
)


def test_agent_task_broker_downstream_install_contract() -> None:
    """Run experiment-local downstream install contract in normal CI discovery."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(EXPERIMENT_TEST), "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
