"""Tests verifier artifact retention hardening."""

from __future__ import annotations

import os
from pathlib import Path

from agent_maintainer.verify import history as verify_history

ENCODING = "utf-8"
RUN_TIMESTAMP_LENGTH = len("20260630T090733123456Z")
TARGET_NAME = "manifest.json"


def test_atomic_text_write_replaces_pointer(tmp_path: Path) -> None:
    """Artifact writes replace latest pointers without temp leftovers."""

    target = tmp_path / TARGET_NAME
    target.write_text("old\n", encoding=ENCODING)
    verify_history.atomic_write_text(target, "new")
    assert target.read_text(encoding=ENCODING) == "new\n"
    assert not list(tmp_path.glob(f".{TARGET_NAME}.*.tmp"))


def test_run_id_has_microsecond_timestamp() -> None:
    """Run ids include microseconds to avoid same-second collisions."""

    run_id = verify_history.build_run_id("full", {"head": "abc"})
    timestamp, profile, digest = run_id.split("-")
    assert len(timestamp) == RUN_TIMESTAMP_LENGTH
    assert timestamp.endswith("Z")
    assert profile == "full"
    assert len(digest) == verify_history.RUN_ID_DIGEST_LENGTH


def test_prune_history_tiebreaks_by_name(tmp_path: Path) -> None:
    """Retention pruning is deterministic when directory mtimes tie."""

    log_dir = tmp_path / ".verify-logs"
    runs_dir = log_dir / verify_history.RUNS_DIR_NAME
    for name in ("run-a", "run-b", "run-c"):
        run_dir = runs_dir / name
        run_dir.mkdir(parents=True)
        os.utime(run_dir, ns=(1, 1))
    verify_history.prune_run_history(log_dir, keep=2)
    assert sorted(path.name for path in runs_dir.iterdir()) == ["run-b", "run-c"]
