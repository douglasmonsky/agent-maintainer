"""Command-level runtime event helpers."""

from __future__ import annotations

from collections.abc import Callable, Collection
from time import monotonic

from agent_maintainer.config.loader import load_config
from agent_maintainer.runtime_events.models import RuntimeEvent
from agent_maintainer.runtime_events.sinks import (
    NullRuntimeEventSink,
    RuntimeEventSink,
    make_runtime_event_sink,
)

CommandCall = Callable[[], int]


def run_with_command_events(
    argv: list[str],
    command_call: CommandCall,
    *,
    known_commands: Collection[str],
) -> int:
    """Run one CLI command while emitting best-effort command events."""

    command = resolve_command_name(argv, known_commands)
    attributes = _command_attributes(argv, command=command)
    sink = _command_sink()
    started_at = monotonic()
    sink.emit(
        RuntimeEvent(
            "command.started",
            command=command,
            attributes=attributes,
        ),
    )
    try:
        exit_code = command_call()
    except Exception as exc:
        sink.emit(
            RuntimeEvent(
                "command.exception",
                severity="error",
                command=command,
                status="exception",
                duration_ms=_duration_ms(started_at),
                attributes={
                    **attributes,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            ),
        )
        raise

    sink.emit(
        RuntimeEvent(
            "command.finished",
            severity="info" if exit_code == 0 else "error",
            command=command,
            status="pass" if exit_code == 0 else "fail",
            duration_ms=_duration_ms(started_at),
            exit_code=exit_code,
            attributes=attributes,
        ),
    )
    return exit_code


def resolve_command_name(argv: list[str], known_commands: Collection[str]) -> str:
    """Return safe command name without recording arbitrary raw argv text."""

    if not argv or argv[0] in {"-h", "--help"}:
        return "help"
    if argv[0] in known_commands:
        return argv[0]
    return "unknown"


def _command_attributes(argv: list[str], *, command: str) -> dict[str, object]:
    """Return compact, non-sensitive command metadata."""

    return {
        "argc": len(argv),
        "has_options": any(arg.startswith("-") for arg in argv[1:]),
        "known_command": command not in {"help", "unknown"},
    }


def _command_sink() -> RuntimeEventSink:
    """Return configured command event sink without changing command behavior."""

    try:
        config = load_config()
    except (OSError, ValueError, TypeError):
        return NullRuntimeEventSink()
    return make_runtime_event_sink(config)


def _duration_ms(started_at: float) -> int:
    """Return elapsed milliseconds for command lifecycle events."""

    return max(0, int((monotonic() - started_at) * 1000))
