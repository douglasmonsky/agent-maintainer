"""Tests native SpotBugs verification without baseline mutation."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.java import runner
from agent_maintainer.ecosystems.java.reports.spotbugs import SpotBugsEvidenceError
from agent_maintainer.models import FULL_PROFILE

BASELINE_PATH = "config/spotbugs/baseline.xml"
REPORT_PATH = "build/reports/spotbugs/main.xml"
SPOTBUGS_TASK = "spotbugsMain"
TEXT_ENCODING = "utf-8"


def test_verification_never_changes_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fresh report validation is read-only for the committed native filter."""
    baseline = write_baseline(tmp_path)
    before = baseline.read_bytes()
    configure_runner(monkeypatch, tmp_path, write_report=True)

    outcome = runner.run_group(tmp_path, "static", FULL_PROFILE)

    assert outcome.exit_code == 0
    assert outcome.payload["spotbugs"] == {"reports": 1, "findings": 1}
    assert baseline.read_bytes() == before


def test_verification_refuses_stale_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Executed success cannot reuse an unchanged pre-run report."""
    write_baseline(tmp_path)
    write_spotbugs_report(tmp_path)
    configure_runner(monkeypatch, tmp_path, write_report=False)

    with pytest.raises(SpotBugsEvidenceError, match="stale"):
        runner.run_group(tmp_path, "static", FULL_PROFILE)


def configure_runner(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    *,
    write_report: bool,
) -> None:
    """Install deterministic native-ratchet runner doubles."""
    expectation = JavaReportExpectation("spotbugs", (SPOTBUGS_TASK,), (REPORT_PATH,))
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotbugs",),
            spotbugs_tasks=(SPOTBUGS_TASK,),
            spotbugs_baseline=BASELINE_PATH,
            reports=(expectation,),
        )
    )
    resolved = runner.wrapper.ResolvedGradleWrapper(repo, repo, repo / "gradlew")

    monkeypatch.setattr(runner, "_load_java_config", Mock(return_value=config))
    monkeypatch.setattr(runner.wrapper, "resolve_gradle_wrapper", Mock(return_value=resolved))
    monkeypatch.setattr(runner, "_run_wrapper", partial(run_wrapper, repo, write_report))


def run_wrapper(
    repo: Path,
    write_report: bool,
    *_args: object,
) -> runner.subprocess.CompletedProcess[str]:
    """Simulate one wrapper run and optional fresh report write."""
    if write_report:
        write_spotbugs_report(repo)
    return runner.subprocess.CompletedProcess(
        args=(),
        returncode=0,
        stdout=f"> Task :{SPOTBUGS_TASK}\n",
    )


def write_baseline(root: Path) -> Path:
    """Write one committed native filter sentinel."""
    baseline = root / BASELINE_PATH
    baseline.parent.mkdir(parents=True)
    baseline.write_text("<FindBugsFilter/>\n", encoding=TEXT_ENCODING)
    return baseline


def write_spotbugs_report(root: Path) -> Path:
    """Write one successful report after the pre-run snapshot."""
    report = root / REPORT_PATH
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "<BugCollection><BugInstance type='NP_NULL'>"
        "<Class classname='example.App'/></BugInstance>"
        "<Errors errors='0' missingClasses='0'/></BugCollection>",
        encoding=TEXT_ENCODING,
    )
    return report
