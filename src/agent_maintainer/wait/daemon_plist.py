"""LaunchAgent plist rendering for wait daemon."""

from __future__ import annotations

import plistlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LaunchAgentPlist:
    """Inputs for one repo wait daemon LaunchAgent plist."""

    path: Path
    root: Path
    label: str
    log_path: Path
    python_executable: str
    interval_seconds: int
    idle_timeout_seconds: int


def write_launch_agent_plist(config: LaunchAgentPlist) -> None:
    """Write LaunchAgent plist without private Codex metadata."""

    payload = {
        "Label": config.label,
        "ProgramArguments": [
            config.python_executable,
            "-m",
            "agent_maintainer",
            "wait",
            "daemon",
            "run",
            "--root",
            str(config.root),
            "--interval",
            str(config.interval_seconds),
            "--idle-timeout",
            str(config.idle_timeout_seconds),
        ],
        "WorkingDirectory": str(config.root),
        "StandardOutPath": str(config.log_path),
        "StandardErrorPath": str(config.log_path),
        "EnvironmentVariables": {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(config.root / "src"),
        },
        "RunAtLoad": False,
    }
    with config.path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)
