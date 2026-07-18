"""Bounded historical contract-state Git tests."""

from __future__ import annotations

import subprocess  # nosec B404
from collections.abc import Iterable
from pathlib import Path

import pytest

from agent_maintainer.contracts import git_base
from agent_maintainer.contracts.baseline import render_baseline
from agent_maintainer.contracts.limits import MAX_INPUT_BYTES
from agent_maintainer.contracts.models import ContractBaseline, GitContractError

BASE_SHA = "a" * 40
POLICY_PATH = ".agent-maintainer/contracts.toml"
BASELINE_PATH = ".agent-maintainer/contracts-baseline.json"
VALID_POLICY = b"""version = 1
package_version_file = "pyproject.toml"
pre_one_breaking = "prerelease"
stable_breaking = "major"
"""
VALID_BASELINE = render_baseline(
    ContractBaseline(package_version="0.1.0b9")
).encode()


def _tree(*, policy_mode: str = "100644", baseline: bool = True) -> bytes:
    entries = [f"{policy_mode} blob {'b' * 40}\t{POLICY_PATH}\0"]
    if baseline:
        entries.append(f"100644 blob {'c' * 40}\t{BASELINE_PATH}\0")
    return "".join(entries).encode()


class RecordingGitRunner:
    """Return queued Git bytes and retain every exact command."""

    def __init__(self, outputs: Iterable[bytes | BaseException]) -> None:
        self.outputs = iter(outputs)
        self.commands: list[tuple[str, ...]] = []

    def __call__(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        max_bytes: int,
    ) -> bytes:
        assert cwd.is_absolute()
        assert max_bytes > 0
        self.commands.append(command)
        output = next(self.outputs)
        if isinstance(output, BaseException):
            raise output
        return output


def test_base_ref_is_resolved_before_blob_reads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Untrusted refs never appear in historical blob selectors."""
    runner = RecordingGitRunner(
        (BASE_SHA.encode() + b"\n", _tree(), VALID_POLICY, VALID_BASELINE)
    )
    monkeypatch.setattr(git_base, "run_git", runner)

    state = git_base.read_base_contract_files(tmp_path, "origin/main")

    assert state is not None
    assert state.commit == BASE_SHA
    assert runner.commands[0][-2:] == ("origin/main^{commit}", "--")
    assert all("origin/main" not in part for command in runner.commands[1:] for part in command)
    assert all(command[-1] == "--" for command in runner.commands[2:])


@pytest.mark.parametrize("base_ref", ("", "--help", "main..other", "bad ref", "@{upstream}"))
def test_base_ref_rejects_option_shaped_or_malformed_values(
    base_ref: str,
    tmp_path: Path,
) -> None:
    """Only one bounded revision atom reaches Git."""
    with pytest.raises(GitContractError, match="base ref"):
        git_base.resolve_base_commit(tmp_path, base_ref)


def test_missing_base_contract_files_return_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A valid historical commit may predate contract adoption."""
    runner = RecordingGitRunner((BASE_SHA.encode(), b""))
    monkeypatch.setattr(git_base, "run_git", runner)

    assert git_base.read_base_contract_files(tmp_path, "main") is None


def test_partial_base_contract_state_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Policy and generated evidence must enter history together."""
    runner = RecordingGitRunner((BASE_SHA.encode(), _tree(baseline=False)))
    monkeypatch.setattr(git_base, "run_git", runner)

    with pytest.raises(GitContractError, match="partial"):
        git_base.read_base_contract_files(tmp_path, "main")


def test_symlink_like_tree_entries_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Historical policy cannot be sourced through a Git symlink entry."""
    runner = RecordingGitRunner((BASE_SHA.encode(), _tree(policy_mode="120000")))
    monkeypatch.setattr(git_base, "run_git", runner)

    with pytest.raises(GitContractError, match="regular blob"):
        git_base.read_base_contract_files(tmp_path, "main")


@pytest.mark.parametrize(
    ("policy_bytes", "message"),
    (
        (b"x" * (MAX_INPUT_BYTES + 1), "size limit"),
        (b"\xff", "UTF-8"),
    ),
)
def test_invalid_historical_blob_content_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    policy_bytes: bytes,
    message: str,
) -> None:
    """Oversized and non-UTF-8 historical inputs fail before decoding policy."""
    runner = RecordingGitRunner((BASE_SHA.encode(), _tree(), policy_bytes))
    monkeypatch.setattr(git_base, "run_git", runner)

    with pytest.raises(GitContractError, match=message):
        git_base.read_base_contract_files(tmp_path, "main")


def test_subprocess_failure_does_not_echo_git_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Git diagnostics expose bounded ref identity, never arbitrary stderr."""
    failure = subprocess.CalledProcessError(1, ("git",), stderr=b"secret-token")
    runner = RecordingGitRunner((failure,))
    monkeypatch.setattr(git_base, "run_git", runner)

    with pytest.raises(GitContractError) as raised:
        git_base.resolve_base_commit(tmp_path, "main")

    assert "main" in str(raised.value)
    assert "secret-token" not in str(raised.value)


def test_git_path_changes_are_structured_once_from_resolved_commit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Migration checks receive only normalized current or destination paths."""
    output = (
        b"M\0CHANGELOG.md\0"
        b"R100\0docs/old.md\0docs/new.md\0"
        b"D\0docs/gone.md\0"
    )
    runner = RecordingGitRunner((output,))
    monkeypatch.setattr(git_base, "run_git", runner)

    changes = git_base.read_git_changes(tmp_path, BASE_SHA)

    assert [(item.path, item.kind) for item in changes] == [
        ("CHANGELOG.md", "modified"),
        ("docs/new.md", "renamed"),
        ("docs/gone.md", "deleted"),
    ]
    assert changes[1].old_path == "docs/old.md"
    assert runner.commands[0][1:] == (
        "diff",
        "--name-status",
        "-z",
        "-M",
        BASE_SHA,
        "--",
    )


def test_git_runner_never_uses_a_shell(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Git execution receives an argv tuple and disables shell interpretation."""
    observed: dict[str, object] = {}

    class Process:
        returncode = 0

        def communicate(self, *, timeout: int | None = None) -> tuple[bytes, None]:
            if timeout is not None:
                assert timeout > 0
            return BASE_SHA.encode(), None

        def kill(self) -> None:
            self.returncode = -9

    def fake_popen(command: tuple[str, ...], **kwargs: object) -> Process:
        observed["command"] = command
        observed.update(kwargs)
        return Process()

    monkeypatch.setattr(git_base.subprocess, "Popen", fake_popen)

    assert git_base.resolve_base_commit(tmp_path, "main") == BASE_SHA
    assert isinstance(observed["command"], tuple)
    assert observed["shell"] is False
