"""Bounded subprocess execution for agent hooks."""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path
from tempfile import TemporaryFile
from typing import TextIO

from agent_maintainer.hooks import audit as hook_audit

HOOK_SUBPROCESS_OUTPUT_LIMIT = 16_000
HOOK_OUTPUT_OMISSION = (
    "\n[Agent Maintainer hook omitted verifier output beyond "
    f"{HOOK_SUBPROCESS_OUTPUT_LIMIT} characters.]"
)


def run_verifier_bounded(command: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Run verifier without accumulating unbounded stdout/stderr in memory."""

    with (
        TemporaryFile("w+", encoding="utf-8") as stdout_file,
        TemporaryFile("w+", encoding="utf-8") as stderr_file,
    ):
        result = subprocess.run(  # nosec B603
            command,
            cwd=repo_root,
            env=hook_audit.hook_env_with_src(repo_root),
            text=True,
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
        )
        return subprocess.CompletedProcess(
            command,
            result.returncode,
            bounded_file_text(stdout_file),
            bounded_file_text(stderr_file),
        )


def bounded_file_text(file_obj: TextIO) -> str:
    """Return bounded text from a verifier output file object."""

    file_obj.seek(0)
    text = file_obj.read(HOOK_SUBPROCESS_OUTPUT_LIMIT + 1)
    if len(text) <= HOOK_SUBPROCESS_OUTPUT_LIMIT:
        return text
    return text[:HOOK_SUBPROCESS_OUTPUT_LIMIT] + HOOK_OUTPUT_OMISSION
