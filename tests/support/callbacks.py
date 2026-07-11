"""Typed callback factories for test doubles."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import NoReturn


def constant_callback(value: object) -> Callable[..., object]:
    """Return a fully typed callback that always returns ``value``."""

    def callback(*_args: object, **_kwargs: object) -> object:
        return value

    return callback


def forbidden_callback(message: str) -> Callable[..., NoReturn]:
    """Return a callback that fails immediately when unexpectedly invoked."""

    def callback(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError(message)

    return callback


def completed_process_callback(
    returncode: int,
    *,
    stdout: str = "",
    stderr: str = "",
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a subprocess test double with typed command and keyword inputs."""

    def callback(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    return callback
