"""Tests safe generated-artifact cleanup planning and application."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.doctor import artifact_cleanup
from agent_maintainer.doctor import cli as doctor_cli

ENCODING = "utf-8"
ARGPARSE_ERROR = 2


def generated_artifacts(root: Path) -> tuple[Path, Path]:
    """Create bytecode and duplicate verifier artifacts."""

    bytecode = root / "src" / "demo" / "__pycache__"
    bytecode.mkdir(parents=True)
    (bytecode / "module.cpython-314.pyc").write_bytes(b"generated")
    duplicate = root / ".verify-logs" / "manifest 2.json"
    duplicate.parent.mkdir()
    duplicate.write_text("{}\n", encoding=ENCODING)
    return bytecode, duplicate


def test_artifact_cleanup_plan_includes_only_known_generated_paths(
    tmp_path: Path,
) -> None:
    """Cleanup excludes source-like copies and unknown directories."""

    bytecode, duplicate = generated_artifacts(tmp_path)
    source_copy = tmp_path / "src" / "demo" / "module 2.py"
    source_copy.write_text("value = 1\n", encoding=ENCODING)
    plan_copy = tmp_path / ".agent-maintainer" / "change-plans" / "plan 2.md"
    plan_copy.parent.mkdir(parents=True)
    plan_copy.write_text("# user-authored\n", encoding=ENCODING)

    assert artifact_cleanup.artifact_cleanup_plan(tmp_path) == (
        duplicate,
        bytecode,
    )


def test_artifact_cleanup_is_dry_run_by_default(tmp_path: Path) -> None:
    """Planning reports candidates without deleting them."""

    bytecode, duplicate = generated_artifacts(tmp_path)

    assert artifact_cleanup.prune_generated_artifacts(tmp_path, apply=False) == (
        duplicate,
        bytecode,
    )
    assert bytecode.exists()
    assert duplicate.exists()


def test_artifact_cleanup_apply_removes_only_planned_paths(tmp_path: Path) -> None:
    """Explicit application removes the plan and preserves user files."""

    bytecode, duplicate = generated_artifacts(tmp_path)
    user_file = tmp_path / "src" / "demo" / "module.py"
    user_file.write_text("value = 1\n", encoding=ENCODING)

    assert artifact_cleanup.prune_generated_artifacts(tmp_path, apply=True) == (
        duplicate,
        bytecode,
    )
    assert not bytecode.exists()
    assert not duplicate.exists()
    assert user_file.exists()


def test_artifact_cleanup_refuses_symlink_candidates(tmp_path: Path) -> None:
    """Cleanup never follows or removes a symlinked generated root."""

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "manifest 2.json").write_text("{}\n", encoding=ENCODING)
    verify_logs = tmp_path / ".verify-logs"
    verify_logs.symlink_to(outside, target_is_directory=True)

    assert artifact_cleanup.artifact_cleanup_plan(tmp_path) == ()
    assert artifact_cleanup.prune_generated_artifacts(tmp_path, apply=True) == ()
    assert (outside / "manifest 2.json").exists()


def test_doctor_cleanup_cli_defaults_to_dry_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI requires --apply before mutating cleanup candidates."""

    _bytecode, duplicate = generated_artifacts(tmp_path)

    assert doctor_cli.main(["--root", str(tmp_path), "--prune-artifacts"]) == 0
    assert duplicate.exists()
    assert "WOULD REMOVE .verify-logs/manifest 2.json" in capsys.readouterr().out


def test_doctor_cleanup_cli_rejects_apply_without_prune(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The mutation flag cannot be supplied to an ordinary doctor run."""

    with pytest.raises(SystemExit) as error:
        doctor_cli.main(["--root", str(tmp_path), "--apply"])

    assert error.value.code == ARGPARSE_ERROR
    assert "--apply requires --prune-artifacts" in capsys.readouterr().err
