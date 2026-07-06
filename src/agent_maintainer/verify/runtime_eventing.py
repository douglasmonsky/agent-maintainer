"""Verifier-facing runtime event helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.models import RuntimeEvent
from agent_maintainer.runtime_events.sinks import RuntimeEventSink, make_runtime_event_sink

VERIFY_COMMAND = "verify"


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
                command=VERIFY_COMMAND,
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
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                status=status,
                exit_code=exit_code,
                attributes={"log_dir": str(log_dir)},
            ),
        )

    def selected(self, checks: Sequence[Any]) -> None:
        """Emit selected-check summary for one verifier profile."""
        self.sink.emit(
            RuntimeEvent(
                "checks.selected",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                attributes={
                    "count": len(checks),
                    "checks": [_name(check) for check in checks],
                },
            ),
        )

    def check_started(self, check: Any) -> None:
        """Emit check started runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "check.started",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                check=_name(check),
            ),
        )

    def check_finished(self, result: Any) -> None:
        """Emit check completed runtime event."""
        status = _result_status(result)
        passed = bool(getattr(result, "passed", False))
        exit_code = _exit_code(result)
        self.sink.emit(
            RuntimeEvent(
                "check.finished",
                severity="info" if passed else "error",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                check=_name(result),
                status=status,
                exit_code=exit_code,
                attributes=_result_attributes(result),
            ),
        )
        if getattr(result, "skipped", False):
            self.sink.emit(
                RuntimeEvent(
                    "check.skipped",
                    command=VERIFY_COMMAND,
                    profile=self.profile,
                    run_id=self.run_id,
                    check=_name(result),
                    status=status,
                    attributes=_result_attributes(result),
                ),
            )
        elif not passed:
            self.sink.emit(
                RuntimeEvent(
                    "check.failed",
                    severity="error",
                    command=VERIFY_COMMAND,
                    profile=self.profile,
                    run_id=self.run_id,
                    check=_name(result),
                    status=status,
                    exit_code=exit_code,
                    attributes=_result_attributes(result),
                ),
            )

    def check_exception(self, check: Any, exc: Exception) -> None:
        """Emit compact check exception runtime event."""
        self.sink.emit(
            RuntimeEvent(
                "check.exception",
                severity="error",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                check=_name(check),
                status="exception",
                attributes={
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ),
        )


@dataclass(frozen=True)
class ArtifactRuntimeEvents:
    """Runtime event adapter for verifier artifact writes."""

    sink: RuntimeEventSink
    profile: str
    run_id: str

    def artifact_written(self, *, path: str, kind: str) -> None:
        """Emit verifier artifact write event."""
        self.sink.emit(
            RuntimeEvent(
                "artifact.written",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                attributes={"path": path, "kind": kind},
            ),
        )

    def artifact_removed(self, *, path: str, kind: str) -> None:
        """Emit verifier artifact removal event."""
        self.sink.emit(
            RuntimeEvent(
                "artifact.removed",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                attributes={"path": path, "kind": kind},
            ),
        )

    def artifact_retention_pruned(
        self,
        *,
        log_dir: Path,
        pruned_count: int,
        keep: int,
    ) -> None:
        """Emit retained artifact pruning event."""
        self.sink.emit(
            RuntimeEvent(
                "artifact.retention_pruned",
                command=VERIFY_COMMAND,
                profile=self.profile,
                run_id=self.run_id,
                attributes={
                    "log_dir": str(log_dir),
                    "pruned_count": pruned_count,
                    "keep": keep,
                },
            ),
        )


def artifact_events_for(profile_events: ProfileRuntimeEvents) -> ArtifactRuntimeEvents:
    """Return artifact event adapter sharing a profile event sink."""

    return ArtifactRuntimeEvents(
        sink=profile_events.sink,
        profile=profile_events.profile,
        run_id=profile_events.run_id,
    )


def run_reused(
    profile_events: ProfileRuntimeEvents,
    *,
    exit_code: int,
    log_dir: Path,
    fingerprint: dict[str, object],
) -> None:
    """Emit same-state verifier result reuse event."""

    profile_events.sink.emit(
        RuntimeEvent(
            "verifier.reused",
            command=VERIFY_COMMAND,
            profile=profile_events.profile,
            run_id=profile_events.run_id,
            status="reused",
            exit_code=exit_code,
            attributes={"log_dir": str(log_dir), "fingerprint": fingerprint},
        ),
    )


def run_fresh(
    profile_events: ProfileRuntimeEvents,
    *,
    log_dir: Path,
    fingerprint: dict[str, object],
) -> None:
    """Emit fresh verifier execution event."""

    profile_events.sink.emit(
        RuntimeEvent(
            "verifier.fresh",
            command=VERIFY_COMMAND,
            profile=profile_events.profile,
            run_id=profile_events.run_id,
            status="fresh",
            attributes={"log_dir": str(log_dir), "fingerprint": fingerprint},
        ),
    )


def manual_escalation(
    profile_events: ProfileRuntimeEvents,
    *,
    fingerprint: dict[str, object],
) -> None:
    """Emit explicit manual verifier escalation event."""

    profile_events.sink.emit(
        RuntimeEvent(
            "manual.escalation",
            command=VERIFY_COMMAND,
            profile=profile_events.profile,
            run_id=profile_events.run_id,
            status="requested",
            attributes={"fingerprint": fingerprint},
        ),
    )


def _result_status(result: Any) -> str:
    """Return compact check status for runtime events."""

    if getattr(result, "skipped", False):
        return str(getattr(result, "skip_status", "")) or "skipped"
    if getattr(result, "passed", False):
        return "pass"
    return "fail"


def _result_attributes(result: Any) -> dict[str, object]:
    """Return compact check result attributes for runtime events."""

    attributes: dict[str, object] = {
        "log_path": str(getattr(result, "log_path", "")),
        "artifact_paths": list(getattr(result, "artifact_paths", ())),
        "artifact_sensitivity": str(getattr(result, "artifact_sensitivity", "")),
    }
    skip_status = str(getattr(result, "skip_status", ""))
    if skip_status:
        attributes["skip_status"] = skip_status
    return attributes


def _name(source: Any) -> str:
    """Return compact runtime event source name."""

    return str(getattr(source, "name", "unknown"))


def _exit_code(result: Any) -> int | None:
    """Return result exit code if present and integer-like."""

    exit_code = getattr(result, "exit_code", None)
    if exit_code is None:
        return None
    return int(exit_code)
