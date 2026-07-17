"""Tests task-scoped Gradle outcomes and pre-run report snapshots."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent_maintainer.config.java import JavaReportExpectation
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.java.observations import (
    GradleTaskState,
    build_gradle_observation,
    snapshot_reports,
)

TEXT_ENCODING = "utf-8"
SPOTBUGS_TASK = "spotbugsMain"


def test_observation_keeps_task_scope(tmp_path: Path) -> None:
    """Requested task order controls parsed outcomes and attached snapshots."""
    report = tmp_path / "build" / "reports" / "spotbugs" / "main.xml"
    report.parent.mkdir(parents=True)
    report.write_text("<BugCollection/>\n", encoding=TEXT_ENCODING)
    expectations = (
        JavaReportExpectation(
            "spotbugs",
            (SPOTBUGS_TASK,),
            ("build/reports/spotbugs/main.xml",),
        ),
        JavaReportExpectation("test", ("test",), ("build/test-results/test/*.xml",)),
    )

    snapshots = snapshot_reports(tmp_path, expectations, (SPOTBUGS_TASK, ":app:test"))
    observation = build_gradle_observation(
        (SPOTBUGS_TASK, ":app:test"),
        "> Task :spotbugsMain FROM-CACHE\n> Task :app:test UP-TO-DATE\n",
        0,
        snapshots,
    )

    assert tuple(item.task for item in observation.task_outcomes) == (
        SPOTBUGS_TASK,
        ":app:test",
    )
    assert tuple(item.state for item in observation.task_outcomes) == (
        GradleTaskState.FROM_CACHE,
        GradleTaskState.UP_TO_DATE,
    )
    assert observation.pre_run_reports[0].tasks == (SPOTBUGS_TASK,)
    assert observation.pre_run_reports[0].sha256 == hashlib.sha256(report.read_bytes()).hexdigest()


def test_ambiguous_task_is_rejected() -> None:
    """Two module task lines cannot satisfy one unqualified request."""
    output = "> Task :app:test UP-TO-DATE\n> Task :lib:test UP-TO-DATE\n"

    with pytest.raises(JavaConfigurationError, match="ambiguous requested Gradle task"):
        build_gradle_observation(("test",), output, 0, ())


def test_missing_task_is_rejected() -> None:
    """A requested task absent from plain Gradle output fails closed."""
    with pytest.raises(JavaConfigurationError, match="missing requested Gradle task"):
        build_gradle_observation((SPOTBUGS_TASK,), "> Task :compileJava\n", 0, ())


def test_snapshot_rejects_symlink_escape(tmp_path: Path) -> None:
    """A matching report symlink may not resolve outside gradle_root."""
    outside = tmp_path.parent / "outside-spotbugs.xml"
    outside.write_text("<BugCollection/>\n", encoding=TEXT_ENCODING)
    report = tmp_path / "build" / "reports" / "spotbugs" / "main.xml"
    report.parent.mkdir(parents=True)
    report.symlink_to(outside)
    expectations = (
        JavaReportExpectation(
            "spotbugs",
            (SPOTBUGS_TASK,),
            ("build/reports/spotbugs/main.xml",),
        ),
    )

    with pytest.raises(JavaConfigurationError, match="escapes Gradle root"):
        snapshot_reports(tmp_path, expectations, (SPOTBUGS_TASK,))


def test_unrequested_report_is_ignored(tmp_path: Path) -> None:
    """Old reports for unrequested tasks never enter observation evidence."""
    report = tmp_path / "build" / "reports" / "spotbugs" / "main.xml"
    report.parent.mkdir(parents=True)
    report.write_text("<BugCollection/>\n", encoding=TEXT_ENCODING)
    expectations = (
        JavaReportExpectation(
            "spotbugs",
            (SPOTBUGS_TASK,),
            ("build/reports/spotbugs/main.xml",),
        ),
    )

    assert snapshot_reports(tmp_path, expectations, ("test",)) == ()
