"""Shell rendering for durable wait commands."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path


def resume_command(root: Path, wait_id: str) -> str:
    """Render the default resume command for one durable wait."""

    return _command(root, "resume", wait_id)


def sweep_command(root: Path, wait_id: str) -> str:
    """Render the one-wait sweep command for one durable wait."""

    return _command(root, "sweep --one", wait_id)


def append_root(command: str, root: str | Path) -> str:
    """Append a shell-safe wait root argument to an existing command."""

    return f"{command} --root {shlex.quote(str(root))}"


def _command(root: Path, action: str, wait_id: str) -> str:
    prefix = _pythonpath_prefix(root)
    executable = shlex.quote(sys.executable)
    return f"{prefix}{executable} -m agent_maintainer wait {action} {shlex.quote(wait_id)}"


def _pythonpath_prefix(root: Path) -> str:
    value = os.environ.get("PYTHONPATH", "")
    if not value:
        return ""
    entries = [
        str((root / entry).resolve()) if not Path(entry).is_absolute() else entry
        for entry in value.split(os.pathsep)
    ]
    return f"PYTHONPATH={shlex.quote(os.pathsep.join(entries))} "
