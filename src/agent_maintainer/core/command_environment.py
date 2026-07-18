"""Local project-aware subprocess environment construction."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from agent_maintainer.core.runtime import hardened_subprocess_env


def tool_search_path() -> str:
    """Build PATH with local virtualenv tools ahead of ambient executables."""

    local_tool_dirs = [
        str(Path(relative))
        for relative in (".venv/bin", "venv/bin", "node_modules/.bin")
        if Path(relative).is_dir()
    ]
    executable_dir = str(Path(sys.executable).parent)
    existing_path = os.environ.get("PATH", "")
    search_dirs = [*local_tool_dirs, executable_dir]
    if existing_path:
        search_dirs.append(existing_path)
    return os.pathsep.join(search_dirs)


def command_env() -> dict[str, str]:
    """Return the subprocess environment used for maintainer commands."""

    env = hardened_subprocess_env()
    env["PATH"] = tool_search_path()
    pythonpath = local_package_pythonpath()
    if pythonpath is not None:
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{pythonpath}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else pythonpath
        )
    return env


def local_package_pythonpath() -> str | None:
    """Return local source package path when running from this kit checkout."""

    src_path = Path("src")
    if (src_path / "agent_maintainer").is_dir():
        return str(src_path)
    return None
