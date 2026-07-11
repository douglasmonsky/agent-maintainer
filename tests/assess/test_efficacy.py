"""Tests local agent efficacy assessment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_context.failures import DEFAULT_CONTEXT_BUDGET
from agent_maintainer.assess import cli, efficacy, efficacy_reporting
from agent_maintainer.assess.efficacy_models import EfficacyMetric
from agent_maintainer.runtime_events.read import RuntimeEventReadResult

LOG_EXTRA_BYTES = 800
EXPECTED_TOKEN_SAVINGS = 200
EXPECTED_DUPLICATE_RATE = 50.0
EXPECTED_FULL_RATE = 100.0
EXPECTED_FAILURE_TO_PASS_MS = 30_000
EXPECTED_BACKGROUND_WAIT_RATE = 50.0


def test_efficacy_rates_from_events(tmp_path: Path) -> None:
    """Report summarizes event-backed efficacy rates."""

    report = _sample_report(tmp_path)
    metrics = _metrics_by_name(report.metrics)

    assert metrics["duplicate_run_avoidance_rate"].value == pytest.approx(
        EXPECTED_DUPLICATE_RATE,
    )
    assert metrics["pointer_follow_through_rate"].value == pytest.approx(
        EXPECTED_FULL_RATE,
    )
    assert metrics["repair_next_action_success_rate"].value == pytest.approx(
        EXPECTED_FULL_RATE,
    )
    assert metrics["first_failure_to_passing_profile_ms"].value == (EXPECTED_FAILURE_TO_PASS_MS)
    assert metrics["wait_helper_success_rate"].value == pytest.approx(
        EXPECTED_FULL_RATE,
    )
    assert metrics["background_wait_registration_rate"].value == pytest.approx(
        EXPECTED_BACKGROUND_WAIT_RATE,
    )
    assert metrics["foreground_wait_blocked_count"].value == 1
    assert metrics["wait_heartbeat_noop_count"].value == 1
    assert metrics["wait_terminal_claim_rate"].value == pytest.approx(
        EXPECTED_FULL_RATE,
    )


def test_efficacy_kinds_and_savings(tmp_path: Path) -> None:
    """Report labels measured, estimated, and unknown metrics."""

    report = _sample_report(tmp_path)
    metrics = _metrics_by_name(report.metrics)

    assert metrics["duplicate_run_avoidance_rate"].kind == "measured"
    assert metrics["pointer_follow_through_rate"].kind == "estimated"
    assert metrics["manual_escalation_rate"].kind == "measured"
    assert metrics["manual_escalation_rate"].value == pytest.approx(0)
    assert metrics["background_wait_registration_rate"].kind == "measured"
    assert metrics["wait_terminal_claim_rate"].kind == "measured"
    assert metrics["repair_capsule_token_savings_proxy"].value == (EXPECTED_TOKEN_SAVINGS)


def test_wait_metrics_unknown_without_runtime_wait_events(tmp_path: Path) -> None:
    """Report unknown wait rates when runtime wait lifecycle events are absent."""

    report = efficacy.summarize_efficacy(
        RuntimeEventReadResult(records=[], files_read=0),
        log_dir=tmp_path,
    )
    metrics = _metrics_by_name(report.metrics)

    assert metrics["background_wait_registration_rate"].value == "unknown"
    assert metrics["background_wait_registration_rate"].kind == "unknown"
    assert metrics["foreground_wait_blocked_count"].value == 0
    assert metrics["wait_heartbeat_noop_count"].value == 0
    assert metrics["wait_terminal_claim_rate"].value == "unknown"
    assert metrics["wait_terminal_claim_rate"].kind == "unknown"


def test_efficacy_text_stays_compact(tmp_path: Path) -> None:
    """Rendered report avoids raw event dumps."""

    report = _sample_report(tmp_path)
    text = efficacy_reporting.render_text(report)

    assert "Agent Efficacy Metrics" in text
    assert "duplicate_run_avoidance_rate: 50.0 percent [measured]" in text
    assert json.dumps(_event_records()[0]) not in text


def test_efficacy_unknowns_without_manifest() -> None:
    """Missing artifacts produce explicit unknown metrics."""

    report = efficacy.summarize_efficacy(RuntimeEventReadResult(), log_dir=Path("missing"))
    metrics = _metrics_by_name(report.metrics)

    assert metrics["repair_capsule_token_savings_proxy"].kind == "unknown"
    assert "unknown metrics need more runtime events or manifests" in report.limitations


def test_efficacy_cli_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Assess efficacy CLI reads bounded event files and renders JSON."""

    events_dir = tmp_path / ".verify-logs" / "events"
    events_dir.mkdir(parents=True)
    (events_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(record) for record in _event_records()),
        encoding="utf-8",
    )

    status = cli.main(["efficacy", "--target", str(tmp_path), "--json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files_read"] == 1
    assert payload["total_events"] == len(_event_records())
    assert any(
        metric["name"] == "wait_helper_success_rate"
        and metric["value"] == pytest.approx(EXPECTED_FULL_RATE)
        for metric in payload["metrics"]
    )


def _sample_report(tmp_path: Path) -> efficacy.EfficacyReport:
    """Return representative efficacy report."""

    _write_manifest(
        tmp_path / "manifest.json",
        log_bytes=DEFAULT_CONTEXT_BUDGET + LOG_EXTRA_BYTES,
    )
    return efficacy.summarize_efficacy(
        RuntimeEventReadResult(records=_event_records(), files_read=1),
        log_dir=tmp_path,
    )


def _event_records() -> list[dict[str, object]]:
    """Return synthetic local runtime events."""

    return [
        {"event_name": "verifier.fresh"},
        {"event_name": "verifier.reused"},
        {
            "event_name": "check.failed",
            "check": "pyright",
            "severity": "error",
            "status": "fail",
            "timestamp": "2026-07-06T20:00:00Z",
        },
        {"event_name": "command.finished", "command": "context", "status": "pass"},
        {
            "event_name": "check.finished",
            "check": "pyright",
            "status": "pass",
            "timestamp": "2026-07-06T20:00:10Z",
        },
        {
            "event_name": "profile.finished",
            "status": "pass",
            "timestamp": "2026-07-06T20:00:30Z",
        },
        {"event_name": "command.finished", "command": "wait", "status": "pass"},
        {
            "event_name": "wait.registered",
            "command": "wait",
            "status": "background",
            "attributes": {
                "background": True,
                "target_id": "321",
                "target_kind": "github-pr",
                "wait_id": "github-pr-321-example",
            },
        },
        {
            "event_name": "wait.registered",
            "command": "wait",
            "status": "foreground",
            "attributes": [],
        },
        {
            "event_name": "wait.foreground_blocked",
            "command": "wait",
            "status": "blocked",
            "attributes": {
                "target_id": "321",
                "target_kind": "github-pr",
                "wait_id": "github-pr-321-example",
            },
        },
        {
            "event_name": "wait.heartbeat_noop",
            "command": "wait",
            "status": "pending",
            "attributes": {
                "target_id": "321",
                "target_kind": "github-pr",
            },
        },
        {
            "event_name": "wait.ready",
            "command": "wait",
            "status": "pass",
            "attributes": {
                "target_id": "321",
                "target_kind": "github-pr",
                "wait_id": "github-pr-321-example",
            },
        },
        {
            "event_name": "wait.terminal_claimed",
            "command": "wait",
            "status": "pass",
            "attributes": {
                "target_id": "321",
                "target_kind": "github-pr",
                "wait_id": "github-pr-321-example",
            },
        },
    ]


def _write_manifest(path: Path, *, log_bytes: int) -> None:
    """Write verifier manifest fixture."""

    path.write_text(
        json.dumps(
            {
                "checks": [
                    None,
                    {
                        "name": "pyright",
                        "status": "failed",
                        "log_bytes": log_bytes,
                    },
                ],
            },
        ),
        encoding="utf-8",
    )


def _metrics_by_name(
    metrics: tuple[EfficacyMetric, ...],
) -> dict[str, EfficacyMetric]:
    """Return metrics keyed by metric name."""

    return {metric.name: metric for metric in metrics}
