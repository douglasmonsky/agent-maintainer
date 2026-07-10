"""Owned child entrypoint for one detached verifier process."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from types import FrameType, TracebackType
from typing import Final

from agent_maintainer.verify import async_state, quiet

RUNNING_STATE_TIMEOUT_SECONDS: Final = 5.0
RUNNING_STATE_POLL_SECONDS: Final = 0.01
INFRASTRUCTURE_ERROR_STATUS: Final = 2
UNHANDLED_EXCEPTION_STATUS: Final = 1
SIGNAL_EXIT_OFFSET: Final = 128


def main(argv: Sequence[str] | None = None) -> int:
    """Wait for durable launch state, run verification, and persist outcome."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    state_path = args.state_path
    _install_cancel_handlers(state_path)
    _install_exception_hook(state_path)
    if not _await_running_state(state_path):
        return _running_state_failure(state_path)
    exit_code = quiet.main(_verify_args(args.verify_args))
    async_state.mark_async_terminal(
        state_path,
        status=(async_state.JOB_STATUS_PASSED if exit_code == 0 else async_state.JOB_STATUS_FAILED),
        exit_code=exit_code,
    )
    return exit_code


def cancel_for_signal(state_path: Path, signum: int) -> None:
    """Persist cancellation before terminating for an external signal."""

    exit_code = SIGNAL_EXIT_OFFSET + signum
    signal_name = signal.Signals(signum).name
    async_state.mark_async_terminal(
        state_path,
        status=async_state.JOB_STATUS_CANCELLED,
        exit_code=exit_code,
        error=f"received signal {signal_name}",
        phase="verify",
    )
    sys.exit(exit_code)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-path", required=True, type=Path)
    parser.add_argument("verify_args", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def _verify_args(arguments: list[str]) -> list[str]:
    if arguments and arguments[0] == "--":
        return arguments[1:]
    return arguments


def _install_cancel_handlers(state_path: Path) -> None:
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, partial(_handle_signal, state_path))


def _install_exception_hook(state_path: Path) -> None:
    sys.excepthook = partial(record_unhandled_exception, state_path)


def record_unhandled_exception(
    state_path: Path,
    exception_type: type[BaseException],
    exception: BaseException,
    traceback: TracebackType | None,
) -> None:
    """Persist an infrastructure error before printing its original traceback."""

    async_state.mark_async_terminal(
        state_path,
        status=async_state.JOB_STATUS_ERROR,
        exit_code=UNHANDLED_EXCEPTION_STATUS,
        error=f"{exception_type.__name__}: {exception}",
        phase="verify",
    )
    sys.__excepthook__(exception_type, exception, traceback)


def _handle_signal(state_path: Path, signum: int, _frame: FrameType | None) -> None:
    cancel_for_signal(state_path, signum)


def _await_running_state(state_path: Path) -> bool:
    deadline = time.monotonic() + RUNNING_STATE_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        state = async_state.read_async_state(state_path)
        if state is not None and state.status == async_state.JOB_STATUS_RUNNING:
            return state.process_id == os.getpid()
        if state is not None and state.terminal:
            return False
        time.sleep(RUNNING_STATE_POLL_SECONDS)
    return False


def _running_state_failure(state_path: Path) -> int:
    state = async_state.read_async_state(state_path)
    if state is not None and state.terminal:
        return state.exit_code or INFRASTRUCTURE_ERROR_STATUS
    async_state.mark_async_terminal(
        state_path,
        status=async_state.JOB_STATUS_ERROR,
        exit_code=INFRASTRUCTURE_ERROR_STATUS,
        error="launcher did not persist running state",
        phase="launch",
    )
    return INFRASTRUCTURE_ERROR_STATUS


if __name__ == "__main__":
    sys.exit(main())
