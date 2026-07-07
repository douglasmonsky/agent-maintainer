"""Wait-command runtime event helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from agent_maintainer.config.loader import load_config
from agent_maintainer.runtime_events.models import RuntimeEvent
from agent_maintainer.runtime_events.sinks import (
    NullRuntimeEventSink,
    RuntimeEventSink,
    make_runtime_event_sink,
)

WAIT_COMMAND = "wait"


@dataclass(frozen=True)
class WaitRuntimeEvents:
    """Runtime event adapter for one wait command target."""

    sink: RuntimeEventSink
    target_kind: str
    target_id: str

    @classmethod
    def create(cls, *, target_kind: str, target_id: str) -> Self:
        """Create wait runtime event adapter from repository config."""

        try:
            sink = make_runtime_event_sink(load_config())
        except (OSError, ValueError, TypeError):
            sink = NullRuntimeEventSink()
        return cls(sink=sink, target_kind=target_kind, target_id=target_id)

    def polled(
        self,
        *,
        attempt: int,
        completed: bool,
        status: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Emit one wait polling observation."""

        self.sink.emit(
            RuntimeEvent(
                "wait.poll",
                command=WAIT_COMMAND,
                run_id=self.target_id,
                status="completed" if completed else "pending",
                attributes={
                    "attempt": attempt,
                    "target_kind": self.target_kind,
                    "target_id": self.target_id,
                    "state": status,
                    **(attributes or {}),
                },
            ),
        )

    def registered(self, *, wait_id: str, background: bool) -> None:
        """Emit one wait registration event."""

        self.sink.emit(
            RuntimeEvent(
                "wait.registered",
                command=WAIT_COMMAND,
                run_id=self.target_id,
                status="background" if background else "foreground",
                attributes={
                    "target_kind": self.target_kind,
                    "target_id": self.target_id,
                    "wait_id": wait_id,
                    "background": background,
                },
            ),
        )

    def foreground_blocked(self, *, wait_id: str) -> None:
        """Emit one Codex foreground-wait block event."""

        self.sink.emit(
            RuntimeEvent(
                "wait.foreground_blocked",
                command=WAIT_COMMAND,
                run_id=self.target_id,
                status="background",
                attributes={
                    "target_kind": self.target_kind,
                    "target_id": self.target_id,
                    "wait_id": wait_id,
                },
            ),
        )

    def swept(
        self,
        *,
        checked: int,
        updated: int,
        pending: int,
        ready: int,
    ) -> None:
        """Emit one wait registry sweep summary event."""

        self.sink.emit(
            RuntimeEvent(
                "wait.swept",
                command=WAIT_COMMAND,
                run_id=self.target_id,
                status="completed",
                attributes={
                    "target_kind": self.target_kind,
                    "target_id": self.target_id,
                    "checked": checked,
                    "updated": updated,
                    "pending": pending,
                    "ready": ready,
                },
            ),
        )

    def ready(self, *, wait_id: str, result: str) -> None:
        """Emit one terminal wait-ready event."""

        self.sink.emit(
            RuntimeEvent(
                "wait.ready",
                command=WAIT_COMMAND,
                run_id=self.target_id,
                status=result,
                attributes={
                    "target_kind": self.target_kind,
                    "target_id": self.target_id,
                    "wait_id": wait_id,
                },
            ),
        )

    def resumed(self, *, wait_id: str) -> None:
        """Emit one automatic wait-resume event."""

        self.sink.emit(
            RuntimeEvent(
                "wait.resumed",
                command=WAIT_COMMAND,
                run_id=self.target_id,
                status="resumed",
                attributes={
                    "target_kind": self.target_kind,
                    "target_id": self.target_id,
                    "wait_id": wait_id,
                },
            ),
        )


def emit_heartbeat_noop(events: WaitRuntimeEvents) -> None:
    """Emit one repo heartbeat sweep with no terminal output."""

    _emit_wait_event(events, "wait.heartbeat_noop", status="pending")


def emit_terminal_claimed(
    events: WaitRuntimeEvents,
    *,
    wait_id: str,
    result: str,
) -> None:
    """Emit one terminal wait claimed by repo heartbeat."""

    _emit_wait_event(
        events,
        "wait.terminal_claimed",
        status=result,
        attributes={"wait_id": wait_id},
    )


def emit_cleaned(events: WaitRuntimeEvents, *, expired_ready: int) -> None:
    """Emit one wait cleanup summary event."""

    _emit_wait_event(
        events,
        "wait.cleaned",
        status="completed",
        attributes={"expired_ready": expired_ready},
    )


def _emit_wait_event(
    events: WaitRuntimeEvents,
    event_name: str,
    *,
    status: str,
    attributes: dict[str, object] | None = None,
) -> None:
    events.sink.emit(
        RuntimeEvent(
            event_name,
            command=WAIT_COMMAND,
            run_id=events.target_id,
            status=status,
            attributes={
                "target_kind": events.target_kind,
                "target_id": events.target_id,
                **(attributes or {}),
            },
        ),
    )
