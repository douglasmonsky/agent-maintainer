"""Root command configuration preflight."""

from __future__ import annotations

import sys
from collections.abc import Callable

from agent_maintainer.config import loader, validation

CommandRunner = Callable[[list[str]], int]
CONFIGURATION_ERROR_STATUS = 2
HELP_FLAGS = frozenset(("-h", "--help"))


class ValidatedCommand:
    """Callable wrapper that refuses behavior under invalid policy."""

    def __init__(self, handler: CommandRunner) -> None:
        self._handler = handler

    def __call__(self, command_args: list[str]) -> int:
        if not configuration_is_valid(command_args):
            return CONFIGURATION_ERROR_STATUS
        return self._handler(command_args)

    def original_handler(self) -> CommandRunner:
        """Return the wrapped handler for inspection and testing."""

        return self._handler


def configuration_is_valid(command_args: list[str]) -> bool:
    """Validate resolved policy before a known command can run behavior."""

    if any(argument in HELP_FLAGS for argument in command_args):
        return True
    try:
        loader.load_config()
    except validation.ConfigValidationError as exc:
        print("FAIL configuration", file=sys.stderr)
        for issue in exc.issues:
            print(f"  {issue.render()}", file=sys.stderr)
        return False
    return True
