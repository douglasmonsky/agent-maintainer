"""Bounded Git readers for historical contract state and path facts."""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.contracts.baseline import parse_baseline
from agent_maintainer.contracts.limits import MAX_INPUT_BYTES
from agent_maintainer.contracts.models import (
    BaselineError,
    ContractBaseline,
    ContractPolicy,
    GitContractError,
    PolicyError,
)
from agent_maintainer.contracts.policy import parse_policy
from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

BASELINE_PATH = ".agent-maintainer/contracts-baseline.json"
POLICY_PATH = ".agent-maintainer/contracts.toml"
CONTRACT_PATHS = (POLICY_PATH, BASELINE_PATH)
GIT_SHA = re.compile(r"^[0-9a-f]{40,64}$")
SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
MAX_REF_OUTPUT = 128
MAX_TREE_OUTPUT = 4_096
MAX_DIFF_OUTPUT = MAX_INPUT_BYTES
GIT_TIMEOUT_SECONDS = 15
TREE_FIELD_COUNT = 3
REGULAR_BLOB_MODES = frozenset(("100644", "100755"))


@dataclass(frozen=True)
class BaseContractState:
    """Parsed authored and generated contract state at one exact commit."""

    commit: str
    policy: ContractPolicy
    baseline: ContractBaseline


@dataclass(frozen=True)
class GitPathChange:
    """One structured current or destination Git path fact."""

    path: str
    kind: str
    old_path: str | None = None


def resolve_base_commit(repo_root: Path, base_ref: str) -> str:
    """Resolve one bounded ref to an exact hexadecimal commit object."""

    _validate_base_ref(base_ref)
    command = (
        _git(),
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{base_ref}^{{commit}}",
        "--",
    )
    try:
        output = run_git(command, cwd=repo_root.resolve(), max_bytes=MAX_REF_OUTPUT)
    except (OSError, subprocess.SubprocessError, GitContractError) as exc:
        raise GitContractError(f"could not resolve base ref {base_ref!r}") from exc
    try:
        commit = output.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise GitContractError(f"base ref {base_ref!r} returned an invalid object ID") from exc
    if not GIT_SHA.fullmatch(commit):
        raise GitContractError(f"base ref {base_ref!r} returned an invalid object ID")
    return commit


def read_base_contract_files(repo_root: Path, base_ref: str) -> BaseContractState | None:
    """Read strict policy and baseline blobs from one exact historical commit."""

    root = repo_root.resolve()
    commit = resolve_base_commit(root, base_ref)
    entries = _contract_tree_entries(root, commit)
    present = frozenset(entries)
    if not present:
        return None
    if present != frozenset(CONTRACT_PATHS):
        raise GitContractError("historical contract state is partial")
    for path, (mode, object_type) in entries.items():
        if mode not in REGULAR_BLOB_MODES or object_type != "blob":
            raise GitContractError(f"historical contract path is not a regular blob: {path}")
    policy_text = _read_contract_blob(root, commit, POLICY_PATH, label="policy")
    baseline_text = _read_contract_blob(root, commit, BASELINE_PATH, label="baseline")
    try:
        policy = parse_policy(policy_text, source=f"{commit}:{POLICY_PATH}")
    except PolicyError as exc:
        raise GitContractError(f"historical contract policy is invalid: {POLICY_PATH}") from exc
    try:
        baseline = parse_baseline(baseline_text, source=f"{commit}:{BASELINE_PATH}")
    except BaselineError as exc:
        raise GitContractError(f"historical contract baseline is invalid: {BASELINE_PATH}") from exc
    return BaseContractState(commit, policy, baseline)


def read_git_changes(repo_root: Path, base_commit: str) -> tuple[GitPathChange, ...]:
    """Read bounded NUL-delimited path changes from a resolved base commit."""

    if not GIT_SHA.fullmatch(base_commit):
        raise GitContractError("Git diff base must be a resolved hexadecimal commit")
    command = (
        _git(),
        "diff",
        "--name-status",
        "-z",
        "-M",
        base_commit,
        "--",
    )
    try:
        output = run_git(command, cwd=repo_root.resolve(), max_bytes=MAX_DIFF_OUTPUT)
        return _parse_name_status(output)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as exc:
        raise GitContractError(f"could not read Git path changes for {base_commit}") from exc


def run_git(command: tuple[str, ...], *, cwd: Path, max_bytes: int) -> bytes:
    """Run one argv-only Git command with bounded stdout and no stderr echo."""

    process = subprocess.Popen(  # nosec B603
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    try:
        output, _stderr = process.communicate(timeout=GIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise GitContractError("Git command exceeded the time limit") from exc
    if len(output) > max_bytes:
        raise GitContractError("Git output exceeded the size limit")
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)
    return output


def _validate_base_ref(base_ref: str) -> None:
    if (
        not SAFE_REF.fullmatch(base_ref)
        or ".." in base_ref
        or "//" in base_ref
        or base_ref.endswith(("/", ".", ".lock"))
        or "/." in base_ref
    ):
        raise GitContractError("base ref must be one bounded revision name")


def _contract_tree_entries(repo_root: Path, commit: str) -> dict[str, tuple[str, str]]:
    command = (_git(), "ls-tree", "-z", commit, "--", *CONTRACT_PATHS)
    try:
        output = run_git(command, cwd=repo_root, max_bytes=MAX_TREE_OUTPUT)
        return _parse_tree(output)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as exc:
        raise GitContractError(f"could not inspect historical contract paths at {commit}") from exc


def _parse_tree(output: bytes) -> dict[str, tuple[str, str]]:
    if output and not output.endswith(b"\0"):
        raise ValueError("Git tree output must end with NUL")
    entries: dict[str, tuple[str, str]] = {}
    for raw_entry in output.rstrip(b"\0").split(b"\0") if output else ():
        metadata, separator, raw_path = raw_entry.partition(b"\t")
        parts = metadata.split(b" ")
        if not separator or len(parts) != TREE_FIELD_COUNT:
            raise ValueError("invalid Git tree entry")
        mode, object_type, _object_id = (part.decode("ascii") for part in parts)
        path = raw_path.decode("utf-8")
        if path not in CONTRACT_PATHS or path in entries:
            raise ValueError("unexpected Git tree path")
        entries[path] = (mode, object_type)
    return entries


def _read_contract_blob(repo_root: Path, commit: str, path: str, *, label: str) -> str:
    command = (_git(), "show", "--no-textconv", f"{commit}:{path}", "--")
    try:
        output = run_git(command, cwd=repo_root, max_bytes=MAX_INPUT_BYTES)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitContractError(f"could not read historical contract {label}: {path}") from exc
    if len(output) > MAX_INPUT_BYTES:
        raise GitContractError(f"historical contract {label} exceeded the size limit: {path}")
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitContractError(f"historical contract {label} must be UTF-8: {path}") from exc


def _parse_name_status(output: bytes) -> tuple[GitPathChange, ...]:
    if not output:
        return ()
    if not output.endswith(b"\0"):
        raise ValueError("Git path changes must end with NUL")
    tokens = output[:-1].split(b"\0")
    changes: list[GitPathChange] = []
    index = 0
    while index < len(tokens):
        status = tokens[index].decode("ascii")
        index += 1
        if status.startswith(("R", "C")):
            if not status[1:].isdigit() or index + 1 >= len(tokens):
                raise ValueError("invalid paired Git path change")
            old_path = _git_path(tokens[index])
            path = _git_path(tokens[index + 1])
            kind = "renamed" if status.startswith("R") else "copied"
            changes.append(GitPathChange(path, kind, old_path))
            index += 2
            continue
        kinds = {
            "A": "added",
            "D": "deleted",
            "M": "modified",
            "T": "type-changed",
            "U": "unmerged",
        }
        if status not in kinds or index >= len(tokens):
            raise ValueError("invalid Git path change")
        changes.append(GitPathChange(_git_path(tokens[index]), kinds[status]))
        index += 1
    return tuple(changes)


def _git_path(value: bytes) -> str:
    try:
        return validate_repo_path(value.decode("utf-8"), label="Git path")
    except (UnicodeDecodeError, RepoPathError) as exc:
        raise ValueError("invalid Git path") from exc


def _git() -> str:
    return shutil.which("git") or "git"
