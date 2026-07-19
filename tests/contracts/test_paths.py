"""Repository-confined contract input path tests."""

import os
from pathlib import Path

import pytest

from agent_maintainer.contracts.models import ContractError
from agent_maintainer.contracts.paths import read_confined_text, resolve_confined_path


def test_confined_text_reads_regular_utf8_file(tmp_path: Path) -> None:
    """A canonical regular repository file is readable."""
    path = tmp_path / "config/contracts.json"
    path.parent.mkdir()
    path.write_text("{}\n", encoding="utf-8")

    assert read_confined_text(tmp_path, "config/contracts.json", label="contract") == "{}\n"


@pytest.mark.parametrize("path", ("/tmp/x", "../x", "a\\b", "./x", "a\0b"))
def test_unsafe_contract_paths_fail_closed(tmp_path: Path, path: str) -> None:
    """Ambiguous and escaping path text is rejected before filesystem access."""
    with pytest.raises(ContractError):
        resolve_confined_path(tmp_path, path, label="contract")


def test_symlink_input_is_rejected(tmp_path: Path) -> None:
    """Configured inputs cannot redirect extraction through symlinks."""
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "contract.json"
    link.symlink_to(target)

    with pytest.raises(ContractError, match="regular file"):
        read_confined_text(tmp_path, "contract.json", label="contract")


def test_special_file_input_is_rejected(tmp_path: Path) -> None:
    """Directory and other nonregular inputs are rejected before opening."""
    directory = tmp_path / "contract.json"
    directory.mkdir()

    with pytest.raises(ContractError, match="regular file"):
        read_confined_text(tmp_path, "contract.json", label="contract")


def test_fifo_input_is_rejected_without_blocking(tmp_path: Path) -> None:
    """FIFO inputs are rejected by metadata before a potentially blocking open."""
    fifo = tmp_path / "contract.json"
    os.mkfifo(fifo)

    with pytest.raises(ContractError, match="regular file"):
        read_confined_text(tmp_path, "contract.json", label="contract")


def test_oversized_input_is_rejected(tmp_path: Path) -> None:
    """Configured inputs are bounded before decoding."""
    path = tmp_path / "large.json"
    path.write_bytes(b"x" * 1_000_001)

    with pytest.raises(ContractError, match="too large"):
        read_confined_text(tmp_path, "large.json", label="contract")
