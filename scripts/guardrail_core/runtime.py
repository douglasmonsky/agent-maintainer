"""Runtime environment policy for guardrail processes."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping

ALLOW_BYTECODE_ENV = "AI_GUARDRAILS_WRITE_BYTECODE"
PYTHON_BYTECODE_ENV = "PYTHONDONTWRITEBYTECODE"
TRUE_ENV_VALUES = frozenset(("1", "true", "yes", "on"))


def bytecode_writes_allowed(environment: Mapping[str, str] | None = None) -> bool:
    """Return whether guardrail runtime should allow Python bytecode writes."""
    source = os.environ if environment is None else environment
    return source.get(ALLOW_BYTECODE_ENV, "").casefold() in TRUE_ENV_VALUES


def disable_bytecode_writes() -> None:
    """Disable bytecode writes in this process unless explicitly allowed."""
    if not bytecode_writes_allowed():
        sys.dont_write_bytecode = True


def hardened_subprocess_env(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return subprocess environment with bytecode writes disabled by default."""
    hardened = dict(os.environ if environment is None else environment)
    if bytecode_writes_allowed(hardened):
        hardened.pop(PYTHON_BYTECODE_ENV, None)
    else:
        hardened[PYTHON_BYTECODE_ENV] = "1"
    return hardened
