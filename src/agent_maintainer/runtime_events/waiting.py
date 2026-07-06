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
