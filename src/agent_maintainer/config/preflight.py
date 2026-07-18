"""Root command configuration preflight."""

from __future__ import annotations

import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

from agent_maintainer.config import loader, validation

CommandRunner = Callable[[list[str]], int]
CONFIGURATION_ERROR_STATUS = 2
HELP_FLAGS = frozenset(("-h", "--help"))


class ValidatedCommand:
    """Callable wrapper that refuses behavior under invalid policy."""

    def __init__(
        self,
        handler: CommandRunner,
        *,
        config_root_option: str | None = None,
    ) -> None:
        self._handler = handler
        self._config_root_option = config_root_option

    def __call__(self, command_args: list[str]) -> int:
        repo_root = _option_path(command_args, self._config_root_option)
        if not configuration_is_valid(command_args, repo_root=repo_root):
            return CONFIGURATION_ERROR_STATUS
        return self._handler(command_args)

    def original_handler(self) -> CommandRunner:
        """Return the wrapped handler for inspection and testing."""

        return self._handler


def lazy_target_command(module_name: str, *, option: str) -> ValidatedCommand:
    """Return a target-aware command that imports its implementation lazily."""
    return ValidatedCommand(
        partial(_run_module_main, module_name),
        config_root_option=option,
    )


def configuration_is_valid(
    command_args: list[str],
    *,
    repo_root: Path | None = None,
) -> bool:
    """Validate resolved policy before a known command can run behavior."""

    if any(argument in HELP_FLAGS for argument in command_args):
        return True
    try:
        loader.load_config(repo_root)
    except validation.ConfigValidationError as exc:
        print("FAIL configuration", file=sys.stderr)
        for issue in exc.issues:
            print(f"  {issue.render()}", file=sys.stderr)
        return False
    return True


def _option_path(command_args: list[str], option: str | None) -> Path | None:
    if option is None:
        return None
    prefix = f"{option}="
    for index, argument in enumerate(command_args):
        if argument.startswith(prefix):
            return Path(argument.removeprefix(prefix))
        if argument == option and index + 1 < len(command_args):
            return Path(command_args[index + 1])
    return None


def _run_module_main(module_name: str, command_args: list[str]) -> int:
    module = __import__(module_name, fromlist=("main",))
    return module.main(command_args)
