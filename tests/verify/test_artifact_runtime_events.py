"""Tests verifier artifact runtime event emission."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.models import CheckResult
from agent_maintainer.verify import artifact_adapters, artifacts

ENCODING = "utf-8"


def empty_event_records() -> list[dict[str, object]]:
    """Return a typed empty runtime-event collection."""

    return []


@dataclass
class RecordingArtifactEvents:
    """Runtime event recorder for artifact tests."""

    written: list[dict[str, object]] = field(default_factory=empty_event_records)
    removed: list[dict[str, object]] = field(default_factory=empty_event_records)
    pruned: list[dict[str, object]] = field(default_factory=empty_event_records)

    def artifact_written(self, *, path: str, kind: str) -> None:
        """Record one artifact write."""

        self.written.append({"path": path, "kind": kind})

    def artifact_removed(self, *, path: str, kind: str) -> None:
        """Record one artifact removal."""

        self.removed.append({"path": path, "kind": kind})

    def artifact_retention_pruned(
        self,
        *,
        log_dir: Path,
        pruned_count: int,
        keep: int,
    ) -> None:
        """Record one retention pruning event."""

        self.pruned.append(
            {
                "log_dir": str(log_dir),
                "pruned_count": pruned_count,
                "keep": keep,
            },
        )


def test_artifact_events_record_failure_writes(tmp_path: Path) -> None:
    """Failure artifacts emit compact written-artifact events."""

    log_dir = tmp_path / ".verify-logs"
    result = failed_result_with_log(log_dir)
    events = RecordingArtifactEvents()

    artifacts.write_run_artifacts(
        log_dir,
        run_context(tmp_path),
        [result],
        runtime_events=events,
    )

    assert artifact_kinds(events.written) == {
        "latest-failure",
        "latest-manifest",
        "pr-summary",
        "run-check-log",
        "run-failure",
        "run-manifest",
    }


def test_artifact_events_record_failure_removal(tmp_path: Path) -> None:
    """Passing runs emit removal event when stale failure pointer is cleared."""

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()
    (log_dir / artifacts.LAST_FAILURE_NAME).write_text("stale\n", encoding=ENCODING)
    events = RecordingArtifactEvents()

    artifacts.write_run_artifacts(
        log_dir,
        run_context(tmp_path),
        [passed_result(log_dir)],
        runtime_events=events,
    )

    assert artifact_kinds(events.removed) == {"latest-failure"}


def test_artifact_events_record_retention_pruning(tmp_path: Path) -> None:
    """Run history pruning emits compact count metadata."""

    log_dir = tmp_path / ".verify-logs"
    config = MaintainerConfig(diagnostic_run_history_limit=1)
    result = failed_result_with_log(log_dir)
    older_events = RecordingArtifactEvents()
    newer_events = RecordingArtifactEvents()

    artifacts.write_run_artifacts(
        log_dir,
        run_context(tmp_path, config=config, run_id="older-full-test"),
        [result],
        runtime_events=older_events,
    )
    artifacts.write_run_artifacts(
        log_dir,
        run_context(tmp_path, config=config, run_id="newer-full-test"),
        [result],
        runtime_events=newer_events,
    )

    assert newer_events.pruned == [
        {
            "log_dir": str(log_dir),
            "pruned_count": 1,
            "keep": 1,
        },
    ]


def artifact_kinds(records: list[dict[str, object]]) -> set[object]:
    """Return artifact kinds from recorded events."""

    return {record["kind"] for record in records}


def run_context(
    repo_root: Path,
    *,
    config: MaintainerConfig | None = None,
    run_id: str = "20260625T100000Z-full-test",
) -> artifact_adapters.RunContext:
    """Return verifier context for artifact runtime event tests."""

    return artifact_adapters.RunContext(
        repo_root=repo_root,
        profile="full",
        base_ref="HEAD",
        compare_branch="origin/main",
        staged=False,
        config=config or MaintainerConfig(),
        run_id=run_id,
    )


def failed_result_with_log(log_dir: Path) -> CheckResult:
    """Return failed check result with a copyable log."""

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ruff.log"
    log_path.write_text("raw lint output\n", encoding=ENCODING)
    return CheckResult(
        "ruff",
        passed=False,
        output="lint failed",
        command=("ruff", "check"),
        exit_code=1,
        log_path=str(log_path),
    )


def passed_result(log_dir: Path) -> CheckResult:
    """Return passing check result."""

    log_dir.mkdir(parents=True, exist_ok=True)
    return CheckResult(
        "ruff",
        passed=True,
        command=("ruff", "check"),
        exit_code=0,
        log_path=str(log_dir / "ruff.log"),
    )
