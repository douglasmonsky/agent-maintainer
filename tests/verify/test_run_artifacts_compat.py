"""Compatibility tests for moved run artifact helpers."""

from __future__ import annotations

import agent_maintainer.verify.artifact_manifest as old_artifact_manifest
import agent_maintainer.verify.git_state as old_git_state
import agent_maintainer.verify.history as old_history
import agent_maintainer.verify.pr_summary as old_pr_summary
import agent_maintainer.verify.pr_summary_support as old_pr_summary_support
import agent_maintainer.verify.timing as old_timing
from agent_run_artifacts import (
    artifact_manifest,
    git_state,
    history,
    pr_summary,
    pr_summary_support,
    timing,
)


def test_old_artifact_manifest_imports_delegate_to_agent_run_artifacts() -> None:
    """Old artifact-manifest import path delegates to extracted package."""

    assert old_artifact_manifest.check_payload is artifact_manifest.check_payload
    assert old_artifact_manifest.result_status is artifact_manifest.result_status
    assert old_artifact_manifest.threshold_snapshot is artifact_manifest.threshold_snapshot


def test_old_history_imports_delegate_to_agent_run_artifacts() -> None:
    """Old run-history import path delegates to extracted package."""

    assert old_history.RUNS_DIR_NAME == history.RUNS_DIR_NAME
    assert old_history.SnapshotArtifacts is history.SnapshotArtifacts
    assert old_history.build_run_id is history.build_run_id
    assert old_history.run_snapshot_dir is history.run_snapshot_dir
    assert old_history.atomic_write_text is history.atomic_write_text
    assert old_history.copy_run_logs is history.copy_run_logs


def test_old_pr_summary_imports_delegate_to_agent_run_artifacts() -> None:
    """Old PR-summary import path delegates to extracted package."""

    assert old_pr_summary.PR_SUMMARY_NAME == pr_summary.PR_SUMMARY_NAME
    assert old_pr_summary.render_pr_summary is pr_summary.render_pr_summary
    assert old_pr_summary.change_plan_lines is pr_summary.change_plan_lines
    assert old_pr_summary.expansion_command_lines is pr_summary.expansion_command_lines


def test_old_pr_summary_support_imports_delegate_to_agent_run_artifacts() -> None:
    """Old PR-summary support import path delegates to extracted package."""

    assert old_pr_summary_support.MAX_PR_SUMMARY_CHARS == (pr_summary_support.MAX_PR_SUMMARY_CHARS)
    assert old_pr_summary_support.summary_rerun_command is (
        pr_summary_support.summary_rerun_command
    )
    assert old_pr_summary_support.result_state is pr_summary_support.result_state
    assert old_pr_summary_support.bounded_summary is pr_summary_support.bounded_summary


def test_old_timing_imports_delegate_to_agent_run_artifacts() -> None:
    """Old timing import path delegates to extracted package."""

    assert old_timing.PROFILE_DURATION_HINTS == timing.PROFILE_DURATION_HINTS
    assert old_timing.run_timing is timing.run_timing
    assert old_timing.profile_duration_hint is timing.profile_duration_hint
    assert old_timing.duration_seconds is timing.duration_seconds


def test_old_git_state_imports_delegate_to_agent_run_artifacts() -> None:
    """Old Git-state import path delegates to extracted package."""

    assert old_git_state.git_state is git_state.git_state
    assert old_git_state.git_output is git_state.git_output
