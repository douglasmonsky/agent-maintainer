"""Agent Maintainer claude-code PR wait hook wrapper."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO_ROOT / "src"))

run_hook = importlib.import_module("agent_maintainer.hooks.pr_wait").run_hook


def main() -> int:
    """Run Agent Maintainer PR wait hook."""

    return run_hook(
        platform="claude-code",
        repo_root=REPO_ROOT,
        async_rewake=True,
    )


if __name__ == "__main__":
    sys.exit(main())
