"""Unit tests for DocSync's low-level filesystem policy helpers."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from docsync.config.io import read_bounded_text, validate_write_target, write_text_file
from docsync.config.paths import (
    PathBoundaryError,
    require_within,
    resolve_directory_within,
    resolve_input_within,
    sensitive_path,
)
from tests.support.callbacks import constant_callback

PRIVATE_FILE_MODE = 0o600


@pytest.mark.parametrize(
    "path",
    (
        "auth.json",
        "client_secret.json",
        "client_secret_desktop.json",
        "credentials.yml",
        "credentials.yaml",
        "secret.json",
        "secret.yml",
        "secret.yaml",
        "kubeconfig",
        "production.tfvars",
        "production.tfvars.json",
        "terraform.tfstate.backup",
        "token.json",
    ),
)
def test_sensitive_credential_and_infrastructure_names_are_detected(path: str) -> None:
    """Common credential and infrastructure-secret filenames fail closed."""

    assert sensitive_path(Path(path))


def test_missing_and_wrong_kind_inputs_are_rejected(tmp_path: Path) -> None:
    """Input and directory resolvers enforce existence and filesystem kind."""
    regular = tmp_path / "file.txt"
    regular.write_text("text\n", encoding="utf-8")
    directory = tmp_path / "directory"
    directory.mkdir()

    with pytest.raises(PathBoundaryError, match="does not exist"):
        resolve_input_within(tmp_path, Path("missing.txt"), label="input")
    assert resolve_input_within(
        tmp_path,
        Path("missing.txt"),
        label="input",
        allow_missing=True,
    ) == (tmp_path / "missing.txt")
    with pytest.raises(PathBoundaryError, match="regular file"):
        resolve_input_within(tmp_path, Path("directory"), label="input")
    with pytest.raises(PathBoundaryError, match="does not exist"):
        resolve_directory_within(
            tmp_path,
            Path("missing"),
            label="directory",
            allow_missing=False,
        )
    with pytest.raises(PathBoundaryError, match="must be a directory"):
        resolve_directory_within(tmp_path, Path("file.txt"), label="directory")


def test_sensitive_directory_and_outside_resolved_path_are_rejected(tmp_path: Path) -> None:
    """Sensitive names and already-resolved outside paths fail closed."""
    (tmp_path / ".ssh").mkdir()

    assert sensitive_path(Path(".ssh/config"))
    with pytest.raises(PathBoundaryError, match="sensitive"):
        resolve_directory_within(
            tmp_path,
            Path(".ssh"),
            label="directory",
            reject_sensitive=True,
        )
    with pytest.raises(PathBoundaryError, match="must remain under"):
        require_within(tmp_path, tmp_path.parent / "outside", label="output")


def test_bounded_reader_rejects_missing_oversized_and_non_utf8_files(tmp_path: Path) -> None:
    """The descriptor reader reports each unsafe text input class."""
    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"too large")
    binary = tmp_path / "binary.txt"
    binary.write_bytes(b"\xff")

    with pytest.raises(PathBoundaryError, match="Cannot read"):
        read_bounded_text(tmp_path / "missing.txt", label="input")
    with pytest.raises(PathBoundaryError, match="exceeds"):
        read_bounded_text(oversized, label="input", max_bytes=2)
    with pytest.raises(PathBoundaryError, match="UTF-8"):
        read_bounded_text(binary, label="input")


def test_bounded_reader_catches_growth_after_descriptor_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The post-read ceiling catches content that outgrows its inspected metadata."""
    path = tmp_path / "growing.txt"
    path.write_text("grown", encoding="utf-8")
    monkeypatch.setattr(
        os,
        "fstat",
        constant_callback(SimpleNamespace(st_mode=stat.S_IFREG, st_size=0)),
    )

    with pytest.raises(PathBoundaryError, match="exceeds"):
        read_bounded_text(path, label="input", max_bytes=2)


def test_atomic_writer_preserves_mode_and_rejects_special_target(tmp_path: Path) -> None:
    """Atomic replacement preserves basic mode and never replaces a directory."""
    target = tmp_path / "output.txt"
    target.write_text("before\n", encoding="utf-8")
    target.chmod(PRIVATE_FILE_MODE)

    write_text_file(target, "after\n", label="output")

    assert target.read_text(encoding="utf-8") == "after\n"
    assert stat.S_IMODE(target.stat().st_mode) == PRIVATE_FILE_MODE
    with pytest.raises(PathBoundaryError, match="regular file"):
        write_text_file(tmp_path, "nope\n", label="output")
    non_directory_parent = tmp_path / "parent-file"
    non_directory_parent.write_text("text\n", encoding="utf-8")
    with pytest.raises(PathBoundaryError, match="must be a directory"):
        write_text_file(non_directory_parent / "child", "nope\n", label="output")


def test_write_target_preflight_rejects_special_file(tmp_path: Path) -> None:
    """Preflight catches an unsafe later destination before a write batch starts."""
    missing = tmp_path / "missing.txt"

    assert validate_write_target(missing, label="output") == missing
    with pytest.raises(PathBoundaryError, match="regular file"):
        validate_write_target(tmp_path, label="output")


def test_atomic_writer_cleans_temporary_file_after_replace_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed replacement leaves neither destination nor temporary artifact."""
    target = tmp_path / "output.txt"

    def fail_replace(_source: os.PathLike[str], _target: os.PathLike[str]) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(PathBoundaryError, match="Cannot write"):
        write_text_file(target, "content\n", label="output")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_atomic_writer_closes_and_cleans_after_prewrite_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure with an open temporary descriptor is cleaned without mutation."""
    target = tmp_path / "output.txt"

    def fail_chmod(_descriptor: int, _mode: int) -> None:
        raise OSError("chmod failed")

    monkeypatch.setattr(os, "fchmod", fail_chmod)

    with pytest.raises(PathBoundaryError, match="Cannot write"):
        write_text_file(target, "content\n", label="output")

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
