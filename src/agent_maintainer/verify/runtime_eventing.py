"""Verifier-facing runtime event helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.models import RuntimeEvent
from agent_maintainer.runtime_events.sinks import RuntimeEventSink, make_runtime_event_sink


@dataclass(frozen=True)
class ProfileRuntimeEvents:
    """Runtime event adapter for one verifier profile run."""

    sink: RuntimeEventSink
    profile: str
    run_id: str

    @classmethod
    def create(
        cls,
        config: MaintainerConfig,
        *,
        profile: str,
        run_id: str,
    ) -> Self:
        """Create profile runtime event adapter."""
        return cls(
            sink=make_runtime_event_sink(config, stream_id=run_id),
            profile=profile,
            run_id=run_id,
        )

    def started(self, log_dir: Path) -> None:
        """Emit profile started runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "profile.started",
                command="verify",
                profile=self.profile,
                run_id=self.run_id,
                attributes={"log_dir": str(log_dir)},
            ),
        )

    def finished(self, *, status: str, exit_code: int, log_dir: Path) -> None:
        """Emit profile finished runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "profile.finished",
                severity="info" if exit_code == 0 else "error",
                command="verify",
                profile=self.profile,
                run_id=self.run_id,
                status=status,
                exit_code=exit_code,
                attributes={"log_dir": str(log_dir)},
            ),
        )
