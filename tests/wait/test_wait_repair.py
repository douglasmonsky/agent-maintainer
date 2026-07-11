"""Tests stale watcher repair planning and CLI."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from agent_maintainer.wait import cli, wait_repair
from agent_waits.broker import BackgroundWaitRegistration
from agent_waits.constants import WAIT_STATUS_NOTIFY_FAILED, WAIT_STATUS_NOTIFYING
from agent_waits.notifications import claim_terminal_notification
from agent_waits.registry import RegisterWait, WaitRecord, WaitRegistry
from agent_waits.watcher_state import mark_watcher_started, watcher_state

NOW = datetime.fromisoformat("2026-07-10T22:00:00+00:00")
LATER = datetime.fromisoformat("2026-07-10T22:02:00+00:00")
OLD_PID = 123
NEW_PID = 456
STALE_AFTER_SECONDS = 60


def test_repair_restarts_one_stale_dead_watcher(tmp_path: Path) -> None:
    """A dead stale watcher is claimed and replaced once."""

    registry = WaitRegistry(tmp_path)
    record = pending_wait(registry, tmp_path)
    mark_watcher_started(
        registry,
        record,
        strategy="popen",
        pid=OLD_PID,
        now=NOW,
    )

    def starter(root: Path, claimed: WaitRecord) -> BackgroundWaitRegistration:
        return BackgroundWaitRegistration(
            record=claimed,
            watcher_started=True,
            root=str(root),
            watcher_strategy="popen",
            watcher_pid=NEW_PID,
        )

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            stale_after_seconds=STALE_AFTER_SECONDS,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(
            watcher_active=lambda _root, _state: False,
            starter=starter,
        ),
    )

    assert summary.repaired == 1
    assert summary.failed == 0
    repaired = watcher_state(registry.read(record.wait_id))
    assert repaired.strategy == "popen"
    assert repaired.pid == NEW_PID


def test_repair_dry_run_does_not_mutate_record(tmp_path: Path) -> None:
    """Dry-run reports eligibility without taking the repair claim."""

    registry = WaitRegistry(tmp_path)
    record = pending_wait(registry, tmp_path)
    before = registry.read(record.wait_id)

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            stale_after_seconds=STALE_AFTER_SECONDS,
            dry_run=True,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(watcher_active=lambda _root, _state: False),
    )

    assert summary.eligible == 1
    assert summary.repaired == 0
    assert registry.read(record.wait_id) == before


def test_repair_start_failure_persists_only_fixed_code(tmp_path: Path) -> None:
    """A failed restart remains repairable without storing backend diagnostics."""

    registry = WaitRegistry(tmp_path)
    record = pending_wait(registry, tmp_path)

    def fail_start(_root: Path, _record: WaitRecord) -> BackgroundWaitRegistration:
        raise RuntimeError("private-backend-diagnostic")

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            stale_after_seconds=STALE_AFTER_SECONDS,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(
            watcher_active=lambda _root, _state: False,
            starter=fail_start,
        ),
    )
    persisted = registry.read(record.wait_id)
    raw = (registry.waits_dir / persisted.path_name).read_text(encoding="utf-8")

    assert summary.failed == 1
    assert watcher_state(persisted).error_code == "watcher_repair_failed"
    assert "private-backend-diagnostic" not in raw


def test_repair_skips_live_watcher(tmp_path: Path) -> None:
    registry = WaitRegistry(tmp_path)
    record = pending_wait(registry, tmp_path)
    mark_watcher_started(
        registry,
        record,
        strategy="popen",
        pid=OLD_PID,
        now=NOW,
    )

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            stale_after_seconds=STALE_AFTER_SECONDS,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(watcher_active=lambda _root, _state: True),
    )

    assert summary.eligible == 0
    assert summary.skipped == 1


def test_repair_rechecks_liveness_inside_atomic_claim(tmp_path: Path) -> None:
    """A watcher becoming live before the claim cannot be duplicated."""

    registry = WaitRegistry(tmp_path)
    record = pending_wait(registry, tmp_path)
    mark_watcher_started(
        registry,
        record,
        strategy="popen",
        pid=OLD_PID,
        now=NOW,
    )
    liveness = iter((False, True))
    starts: list[str] = []

    def starter(root: Path, claimed: WaitRecord) -> BackgroundWaitRegistration:
        starts.append(claimed.wait_id)
        return BackgroundWaitRegistration(
            record=claimed,
            watcher_started=False,
            root=str(root),
        )

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            stale_after_seconds=STALE_AFTER_SECONDS,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(
            watcher_active=lambda _root, _state: next(liveness),
            starter=starter,
        ),
    )

    assert summary.eligible == 1
    assert summary.repaired == 0
    assert summary.skipped == 1
    assert starts == []
    assert watcher_state(registry.read(record.wait_id)).strategy == "popen"


def test_repair_fails_closed_abandoned_notification_claim(tmp_path: Path) -> None:
    """The repair command also closes stale notifying leases without retrying."""

    registry = WaitRegistry(tmp_path)
    pending = pending_wait(registry, tmp_path)
    ready = registry.complete(
        pending,
        terminal_result="PASS",
        resume_message="done",
        state_data={"status": "passed"},
        now=NOW,
    )
    assert claim_terminal_notification(registry, ready.wait_id, now=NOW) is not None

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            stale_after_seconds=STALE_AFTER_SECONDS,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(watcher_active=lambda _root, _state: False),
    )

    assert summary.notification_failures == 1
    assert registry.read(ready.wait_id).status == WAIT_STATUS_NOTIFY_FAILED


def test_targeted_repair_does_not_change_unrelated_notification(tmp_path: Path) -> None:
    """A wait-id filter applies to notification and watcher repair together."""

    registry = WaitRegistry(tmp_path)
    first_pending = pending_wait(registry, tmp_path, target_id="run-1")
    second_pending = pending_wait(registry, tmp_path, target_id="run-2")
    first = registry.complete(
        first_pending,
        terminal_result="PASS",
        resume_message="done",
        state_data={"status": "passed"},
        now=NOW,
    )
    second = registry.complete(
        second_pending,
        terminal_result="PASS",
        resume_message="done",
        state_data={"status": "passed"},
        now=NOW,
    )
    assert claim_terminal_notification(registry, first.wait_id, now=NOW) is not None
    assert claim_terminal_notification(registry, second.wait_id, now=NOW) is not None

    summary = wait_repair.repair_waits(
        tmp_path,
        request=wait_repair.RepairRequest(
            wait_id=first.wait_id,
            stale_after_seconds=STALE_AFTER_SECONDS,
            now=LATER,
        ),
        hooks=wait_repair.RepairHooks(watcher_active=lambda _root, _state: False),
    )

    assert summary.notification_failures == 1
    assert registry.read(first.wait_id).status == WAIT_STATUS_NOTIFY_FAILED
    assert registry.read(second.wait_id).status == WAIT_STATUS_NOTIFYING


def test_repair_cli_renders_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = wait_repair.RepairSummary(
        checked=1,
        eligible=1,
        repaired=1,
        skipped=0,
        failed=0,
        dry_run=False,
    )
    monkeypatch.setattr(wait_repair, "repair_waits", lambda *_args, **_kwargs: expected)

    status = cli.main(["repair", "--format", "json", "--stale-after", "60"])

    assert status == 0
    assert json.loads(capsys.readouterr().out) == expected.as_dict()


def test_repair_parser_accepts_target_and_dry_run() -> None:
    args = cli.parse_args(
        ["repair", "--wait-id", "wait-1", "--stale-after", "60", "--dry-run"],
    )

    assert args.command == "repair"
    assert args.wait_id == "wait-1"
    assert args.stale_after == STALE_AFTER_SECONDS
    assert args.dry_run is True


def pending_wait(
    registry: WaitRegistry,
    root: Path,
    *,
    target_id: str = "run-1",
) -> WaitRecord:
    return registry.register(
        RegisterWait(root=root, kind="verifier", target_id=target_id, now=NOW),
    )
