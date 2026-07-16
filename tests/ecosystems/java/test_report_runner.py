"""Tests Java runner composition of structured report evidence."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.java import artifacts, baseline, report_evidence, runner
from agent_maintainer.ecosystems.java.findings import JavaFinding
from agent_maintainer.ecosystems.java.report_outcomes import JavaReportEvidenceError
from agent_maintainer.models import FULL_PROFILE

BASELINE_PATH = ".agent-maintainer/java-findings-baseline.json"
REPORT_PATH = "build/reports/checkstyle/main.xml"
TASK = "checkstyleMain"
TEXT_ENCODING = "utf-8"
SOURCE_COMMIT = "a" * 40


def test_runner_compares_fresh_findings_and_emits_sanitized_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching baseline passes and artifacts contain facts, never raw XML."""
    finding = expected_finding()
    write_baseline(tmp_path, finding)
    configure_runner(monkeypatch, tmp_path, returncode=0, report_payload=checkstyle_xml())

    outcome = runner.run_group(tmp_path, "static", FULL_PROFILE)

    assert outcome.exit_code == 0
    reports = outcome.payload["reports"]
    assert isinstance(reports, dict)
    assert reports["baseline"]["new_occurrences"] == 0
    assert reports["findings"][0]["rule"] == "Naming"
    assert "<checkstyle" not in json.dumps(outcome.payload)


def test_runner_fails_new_debt_without_mutating_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unbaselined findings fail policy and verification creates no baseline."""
    configure_runner(monkeypatch, tmp_path, returncode=0, report_payload=checkstyle_xml())

    outcome = runner.run_group(tmp_path, "static", FULL_PROFILE)

    assert outcome.exit_code == 1
    assert outcome.payload["status"] == "report-failed"
    assert not (tmp_path / BASELINE_PATH).exists()


def test_gradle_failure_remains_authoritative_before_report_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing task output or malformed XML cannot replace a Gradle failure."""
    configure_runner(
        monkeypatch,
        tmp_path,
        returncode=1,
        report_payload="<checkstyle>",
        stdout="build failed\n",
    )

    outcome = runner.run_group(tmp_path, "static", FULL_PROFILE)

    assert outcome.exit_code == 1
    assert outcome.payload["status"] == "gradle-failed"
    assert outcome.payload["reports_parsed"] is False


def test_successful_gradle_requires_complete_parseable_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed XML after successful execution fails report evidence closed."""
    configure_runner(
        monkeypatch,
        tmp_path,
        returncode=0,
        report_payload="<checkstyle>",
    )

    with pytest.raises(JavaReportEvidenceError, match="malformed"):
        runner.run_group(tmp_path, "static", FULL_PROFILE)


def test_runner_caps_finding_facts_before_artifact_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Many valid findings retain a bounded useful artifact instead of raw XML."""
    errors = "".join(
        f'<error line="{line}" message="{"x" * 700}" source="com.acme.Rule{line}Check"/>'
        for line in range(1, 31)
    )
    payload = f'<checkstyle><file name="src/App.java">{errors}</file></checkstyle>'
    configure_runner(monkeypatch, tmp_path, returncode=0, report_payload=payload)

    outcome = runner.run_group(tmp_path, "static", FULL_PROFILE)
    reports = outcome.payload["reports"]

    assert isinstance(reports, dict)
    finding_facts = cast(tuple[object, ...], reports["findings"])
    assert len(finding_facts) == report_evidence.MAX_ARTIFACT_FINDINGS
    assert reports["findings_truncated"] is True
    assert len(json.dumps(outcome.payload).encode()) < artifacts.MAX_ARTIFACT_BYTES


def configure_runner(
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    *,
    returncode: int,
    report_payload: str,
    stdout: str | None = None,
) -> None:
    """Install deterministic structured-evidence runner doubles."""
    expectation = JavaReportExpectation("checkstyle", (TASK,), (REPORT_PATH,))
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("checkstyle",),
            checkstyle_tasks=(TASK,),
            findings_baseline=BASELINE_PATH,
            reports=(expectation,),
        ),
    )
    resolved = runner.wrapper.ResolvedGradleWrapper(repo, repo, repo / "gradlew")
    monkeypatch.setattr(runner, "_load_java_config", Mock(return_value=config))
    monkeypatch.setattr(runner.wrapper, "resolve_gradle_wrapper", Mock(return_value=resolved))
    output = stdout if stdout is not None else f"> Task :{TASK}\n"
    monkeypatch.setattr(
        runner,
        "_run_wrapper",
        partial(run_wrapper, repo, report_payload, returncode, output),
    )


def run_wrapper(
    repo: Path,
    report_payload: str,
    returncode: int,
    stdout: str,
    *_args: object,
) -> runner.subprocess.CompletedProcess[str]:
    """Simulate Gradle and write its report after the pre-run snapshot."""
    report = repo / REPORT_PATH
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(report_payload, encoding=TEXT_ENCODING)
    return runner.subprocess.CompletedProcess(args=(), returncode=returncode, stdout=stdout)


def write_baseline(root: Path, finding: JavaFinding) -> None:
    """Write one reviewed findings baseline."""
    baseline.write_baseline(
        root / BASELINE_PATH,
        baseline.create_baseline((finding,), source_commit=SOURCE_COMMIT),
    )


def expected_finding() -> JavaFinding:
    """Return the finding emitted by the Checkstyle fixture."""
    return JavaFinding(
        "checkstyle",
        "Naming",
        "src/main/java/example/App.java",
        "Naming",
        "Name must match",
        "error",
        9,
    )


def checkstyle_xml() -> str:
    """Return one complete Checkstyle report."""
    return """<checkstyle><file name="src/main/java/example/App.java">
      <error line="9" severity="error" message="Name must match"
        source="com.acme.NamingCheck"/>
    </file></checkstyle>"""
