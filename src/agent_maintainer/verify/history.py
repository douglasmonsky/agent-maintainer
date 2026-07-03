"""Compatibility shim for verifier run history helpers."""

from agent_run_artifacts import history

RUNS_DIR_NAME = history.RUNS_DIR_NAME
RUN_ID_DIGEST_LENGTH = history.RUN_ID_DIGEST_LENGTH
SnapshotArtifacts = history.SnapshotArtifacts
build_run_id = history.build_run_id
run_digest = history.run_digest
slug = history.slug
run_snapshot_dir = history.run_snapshot_dir
path_text = history.path_text
prune_run_history = history.prune_run_history
atomic_write_text = history.atomic_write_text
copy_run_logs = history.copy_run_logs
same_path = history.same_path
resolve_path = history.resolve_path
