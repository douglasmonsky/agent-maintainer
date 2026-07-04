"""Runtime event helpers for agent-client hooks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from agent_maintainer.config import loader as config_loader
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.models import RuntimeEvent
from agent_maintainer.runtime_events.sinks import RuntimeEventSink, make_runtime_event_sink


@dataclass(frozen=True)
class HookRuntimeEvents:
    """Runtime event adapter for one hook invocation."""

    sink: RuntimeEventSink
    platform: str
    event: str
    profile: str

    @classmethod
    def create(
        cls,
        repo_root: Path,
        *,
        platform: str,
        event: str,
        profile: str,
    ) -> HookRuntimeEvents:
        """Create hook runtime event adapter for a configured repository."""
        return cls(
            sink=make_runtime_event_sink(_load_hook_config(repo_root)),
            platform=platform,
            event=event,
            profile=profile,
        )

    def invoked(self, *, repo_configured: bool) -> None:
        """Emit hook invocation runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "hook.invoked",
                command="hook",
                profile=self.profile,
                hook_id=_hook_id(self.platform, self.event),
                repo_configured=repo_configured,
                attributes={"platform": self.platform, "event": self.event},
            ),
        )

    def finished(
        self,
        *,
        status: str,
        exit_code: int | None,
        duration_seconds: float,
    ) -> None:
        """Emit hook finished runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "hook.finished",
                severity="info" if exit_code == 0 else "error",
                command="hook",
                profile=self.profile,
                hook_id=_hook_id(self.platform, self.event),
                status=status,
                exit_code=exit_code,
                duration_ms=_duration_ms(duration_seconds),
                repo_configured=True,
                attributes={"platform": self.platform, "event": self.event},
            ),
        )

    def exception(self, exc: Exception, *, duration_seconds: float) -> None:
        """Emit compact hook exception runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "hook.exception",
                severity="error",
                command="hook",
                profile=self.profile,
                hook_id=_hook_id(self.platform, self.event),
                status="exception",
                duration_ms=_duration_ms(duration_seconds),
                repo_configured=True,
                attributes={
                    "platform": self.platform,
                    "event": self.event,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ),
        )


def _load_hook_config(repo_root: Path) -> MaintainerConfig:
    """Load Agent Maintainer config for hook event writing."""
    config = MaintainerConfig()
    raw_config = config_loader.read_pyproject(repo_root / "pyproject.toml")
    if not raw_config:
        raw_config = config_loader.read_neutral_config(
            (
                repo_root / ".agent-maintainer" / "config.toml",
                repo_root / "agent-maintainer.toml",
            ),
        )
    config = config_loader.apply_pyproject(config, raw_config)
    config = config_loader.apply_env(config)
    return _resolve_event_dir(config, repo_root)


def _resolve_event_dir(config: MaintainerConfig, repo_root: Path) -> MaintainerConfig:
    """Resolve hook event directory relative to target repository root."""
    event_dir = Path(config.runtime_events_dir)
    if event_dir.is_absolute():
        return config
    return replace(config, runtime_events_dir=str(repo_root / event_dir))


def _hook_id(platform: str, event: str) -> str:
    """Return stable hook id for runtime events."""
    return f"{platform}:{event}"


def _duration_ms(duration_seconds: float) -> int:
    """Return duration in milliseconds."""
    return int(duration_seconds * 1000)
