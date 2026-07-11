"""Tests repair-fact coverage assessment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.repair_fact_coverage import (
    build_repair_fact_coverage_report,
)
from agent_maintainer.assess.repair_fact_coverage_models import (
    RepairFactCoverageReport,
    RepairFactParserTarget,
)
from agent_maintainer.assess.repair_fact_coverage_reporting import render_json, render_text

CHECK_NAME = "name"
CHECK_STATUS = "status"
FAILED_STATUS = "failed"
PASSED_STATUS = "passed"
EXIT_CODE = "exit_code"
LOG_PATH = "log_path"
LOG_BYTES = "log_bytes"
ARTIFACTS = "artifacts"
PERFECT_COVERAGE = 100.0
MIXED_FAILED_CHECKS = 2
NO_COVERAGE = 0


def test_no_manifest_reports_command(tmp_path: Path) -> None:
    """Missing verifier artifacts produce a compact recovery command."""

    report = build_repair_fact_coverage_report(tmp_path)

    assert report.status == "no-manifest"
    assert report.failed_checks == 0
    assert report.coverage_percent == PERFECT_COVERAGE
    assert report.next_commands == ("python -m agent_maintainer verify --profile precommit",)


def test_no_failure_manifest_has_no_gap(tmp_path: Path) -> None:
    """Passing manifests have no observed repair-fact parser gap."""

    run_dir = write_run(
        tmp_path,
        "20260704T000001Z-precommit-clean",
        [{CHECK_NAME: "ruff", CHECK_STATUS: PASSED_STATUS}],
    )

    report = build_repair_fact_coverage_report(tmp_path, log_dir=tmp_path / ".verify-logs")

    assert report.manifest_path == str(run_dir / "manifest.json")
    assert report.status == "no-failures"
    assert report.failed_checks == 0
    assert report.parser_targets == ()


def test_malformed_check_does_not_hide_failure(tmp_path: Path) -> None:
    """Invalid neighboring checks do not obscure a valid failed record."""

    run_dir = tmp_path / ".verify-logs" / "runs" / "20260704T000001Z-full-mixed"
    run_dir.mkdir(parents=True)
    (run_dir / "custom.log").write_text("failed\n", encoding="utf-8")
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_dir.name,
                "profile": "full",
                "checks": [
                    None,
                    {
                        CHECK_NAME: "custom-check",
                        CHECK_STATUS: FAILED_STATUS,
                        LOG_PATH: "custom.log",
                        LOG_BYTES: 7,
                    },
                ],
            },
        ),
        encoding="utf-8",
    )

    report = build_repair_fact_coverage_report(tmp_path, log_dir=tmp_path / ".verify-logs")

    assert report.failed_checks == 1
    assert report.checks[0].check == "custom-check"


def test_structured_failure_counts_as_covered(tmp_path: Path) -> None:
    """Known structured artifacts count as covered repair facts."""

    run_dir = write_run(
        tmp_path,
        "20260704T000002Z-precommit-ruff",
        [
            {
                "name": "ruff",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "ruff.log",
                LOG_BYTES: 200,
                ARTIFACTS: ["ruff.json"],
            },
        ],
    )
    (run_dir / "ruff.json").write_text(
        json.dumps(
            [
                {
                    "filename": "src/pkg/example.py",
                    "location": {"row": 7, "column": 3},
                    "code": "F401",
                    "message": "unused import",
                },
            ],
        ),
        encoding="utf-8",
    )

    report = build_repair_fact_coverage_report(tmp_path, log_dir=tmp_path / ".verify-logs")

    assert_report_counts(
        report,
        status="structured",
        failed=1,
        structured=1,
        fallback=0,
    )
    assert report.parser_targets == ()


def test_fallback_failure_becomes_parser_target(tmp_path: Path) -> None:
    """Unknown check failures rank as parser targets."""

    write_run(
        tmp_path,
        "20260704T000003Z-full-one",
        [
            {
                "name": "custom-lint",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "custom-lint.log",
                LOG_BYTES: 500,
            },
        ],
    )

    report = build_repair_fact_coverage_report(tmp_path, log_dir=tmp_path / ".verify-logs")

    assert report.status == "fallback-only"
    assert report.coverage_percent == NO_COVERAGE
    assert report.checks[0].fallback_facts == 1
    assert_target(report.parser_targets[0], check="custom-lint", failures=1)


def test_mixed_manifest_ranking(tmp_path: Path) -> None:
    """Ranking prefers frequent fallback failures, then log size."""

    first_run = write_run(
        tmp_path,
        "20260704T000004Z-full-old",
        [
            {
                "name": "custom-small",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "custom-small.log",
                LOG_BYTES: 1_000,
            },
            {
                "name": "custom-frequent",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "custom-frequent.log",
                LOG_BYTES: 100,
            },
        ],
    )
    (first_run / "custom-small.log").write_text("small failed\n", encoding="utf-8")
    second_run = write_run(
        tmp_path,
        "20260704T000005Z-full-new",
        [
            {
                "name": "custom-frequent",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "custom-frequent.log",
                LOG_BYTES: 100,
            },
            {
                "name": "ruff",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "ruff.log",
                LOG_BYTES: 10,
                ARTIFACTS: ["ruff.json"],
            },
        ],
    )
    (second_run / "ruff.json").write_text(
        json.dumps(
            [
                {
                    "filename": "src/pkg/new.py",
                    "location": {"row": 2, "column": 1},
                    "code": "F821",
                    "message": "undefined name",
                },
            ],
        ),
        encoding="utf-8",
    )

    report = build_repair_fact_coverage_report(tmp_path, log_dir=tmp_path / ".verify-logs")

    assert_report_counts(
        report,
        status="mixed",
        failed=MIXED_FAILED_CHECKS,
        structured=1,
        fallback=1,
    )
    assert [target.check for target in report.parser_targets] == [
        "custom-frequent",
        "custom-small",
    ]


def test_json_round_trip_and_text_output(tmp_path: Path) -> None:
    """Renderers expose stable machine JSON and compact text."""

    write_run(
        tmp_path,
        "20260704T000006Z-manual-fail",
        [
            {
                "name": "custom-check",
                CHECK_STATUS: FAILED_STATUS,
                EXIT_CODE: 1,
                LOG_PATH: "custom-check.log",
                LOG_BYTES: 25,
            },
        ],
    )
    report = build_repair_fact_coverage_report(tmp_path, log_dir=tmp_path / ".verify-logs")

    payload = json.loads(render_json(report))
    text = render_text(report)

    assert payload["status"] == "fallback-only"
    assert payload["parser_targets"][0]["check"] == "custom-check"
    assert "Repair-Fact Coverage" in text
    assert "Next parser targets:" in text


def test_cli_supports_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI prints JSON coverage report."""

    write_run(
        tmp_path,
        "20260704T000007Z-precommit-fail",
        [{CHECK_NAME: "custom-check", CHECK_STATUS: FAILED_STATUS, LOG_BYTES: 1}],
    )

    status = cli.main(["repair-fact-coverage", "--target", str(tmp_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["status"] == "fallback-only"
    assert payload["failed_checks"] == 1


def assert_report_counts(
    report: RepairFactCoverageReport,
    *,
    status: str,
    failed: int,
    structured: int,
    fallback: int,
) -> None:
    """Assert core report counters."""

    assert report.status == status
    assert report.failed_checks == failed
    assert report.structured_checks == structured
    assert report.fallback_checks == fallback


def assert_target(target: RepairFactParserTarget, *, check: str, failures: int) -> None:
    """Assert parser target basics."""

    assert target.check == check
    assert target.fallback_failures == failures
    assert "Add log parser" in target.recommendation


def write_run(
    repo_root: Path,
    run_id: str,
    checks: list[dict[str, Any]],
) -> Path:
    """Write one run-scoped manifest fixture."""

    run_dir = repo_root / ".verify-logs" / "runs" / run_id
    run_dir.mkdir(parents=True)
    for check in checks:
        log_path = check.get("log_path")
        if isinstance(log_path, str):
            (run_dir / log_path).write_text(f"{check['name']} failed\n", encoding="utf-8")
    manifest = {
        "run_id": run_id,
        "profile": run_id.split("-")[1],
        "checks": checks,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir
