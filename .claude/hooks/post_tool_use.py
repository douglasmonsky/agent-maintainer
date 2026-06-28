"""Agent Maintainer claude-code PostToolUse hook wrapper."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO_ROOT / "src"))

run_hook = importlib.import_module("agent_maintainer.hooks.runtime").run_hook


def main() -> int:
    """Run shared Agent Maintainer hook runtime."""

    return run_hook(
        platform="claude-code",
        event="PostToolUse",
        profile="fast",
        repo_root=REPO_ROOT,
    )


if __name__ == "__main__":
    sys.exit(main())
