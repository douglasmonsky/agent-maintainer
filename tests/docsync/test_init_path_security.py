"""Security tests for DocSync initialization destinations."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from docsync import cli as docsync_cli
from docsync.config.paths import MAX_REPOSITORY_INPUT_BYTES, PathBoundaryError


def test_init_rejects_symlinked_state_root(tmp_path: Path) -> None:
    """Initialization cannot populate a symlinked outside state directory."""
    repo_root = tmp_path / "repo"
    outside_dir = tmp_path / "outside"
    repo_root.mkdir()
    outside_dir.mkdir()
    (repo_root / ".docsync").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(PathBoundaryError, match="must not contain symlinks"):
        docsync_cli.main(["--repo-root", str(repo_root), "init"])

    assert list(outside_dir.iterdir()) == []


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_init_preflights_special_target(tmp_path: Path) -> None:
    """A later unsafe starter destination leaves earlier starter files absent."""
    repo_root = tmp_path / "repo"
    output_dir = repo_root / ".docsync" / "out"
    output_dir.mkdir(parents=True)
    os.mkfifo(output_dir / ".gitignore")

    with pytest.raises(PathBoundaryError, match="regular file"):
        docsync_cli.main(["--repo-root", str(repo_root), "init", "--force"])

    assert not (repo_root / ".docsync" / "config.yml").exists()
    assert not (repo_root / ".docsync" / "trace.yml").exists()


def test_init_preflights_existing_target(tmp_path: Path) -> None:
    """A later no-force conflict leaves every earlier starter path absent."""
    repo_root = tmp_path / "repo"
    trace_path = repo_root / ".docsync" / "trace.yml"
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text("existing trace\n", encoding="utf-8")

    result = docsync_cli.main(["--repo-root", str(repo_root), "init"])

    assert result == 1
    assert not (repo_root / ".docsync" / "config.yml").exists()
    assert trace_path.read_text(encoding="utf-8") == "existing trace\n"


def test_init_reads_agents_before_writes(tmp_path: Path) -> None:
    """An unsafe AGENTS input aborts before the initializer creates state."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    agents_path = repo_root / "AGENTS.md"
    with agents_path.open("wb") as handle:
        handle.seek(MAX_REPOSITORY_INPUT_BYTES)
        handle.write(b"x")

    with pytest.raises(PathBoundaryError, match="exceeds"):
        docsync_cli.main(["--repo-root", str(repo_root), "init", "--agents"])

    assert not (repo_root / ".docsync" / "config.yml").exists()
