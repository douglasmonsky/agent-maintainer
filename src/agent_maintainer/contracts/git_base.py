"""Bounded Git readers for historical contract state and path facts."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.contracts.baseline import parse_baseline
from agent_maintainer.contracts.git_paths import GitPathChange, parse_name_status
from agent_maintainer.contracts.limits import MAX_INPUT_BYTES
from agent_maintainer.contracts.models import (
    BaselineError,
    ContractBaseline,
    ContractPolicy,
    GitContractError,
    PolicyError,
)
from agent_maintainer.contracts.policy import parse_policy
from agent_maintainer.core import command_run

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
GIT_READ_ERRORS = (OSError, UnicodeError, ValueError)


@dataclass(frozen=True)
class BaseContractState:
    """Parsed authored and generated contract state at one exact commit."""

    commit: str
    policy: ContractPolicy
    baseline: ContractBaseline


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
    except (OSError, GitContractError) as exc:
        raise GitContractError(f"could not resolve base ref {base_ref!r}") from exc
    try:
        commit = output.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise GitContractError(f"base ref {base_ref!r} returned an invalid object ID") from exc
    if not GIT_SHA.fullmatch(commit):
        raise GitContractError(f"base ref {base_ref!r} returned an invalid object ID")
    return commit


def read_base_contract_files(
    repo_root: Path,
    base_ref: str,
) -> BaseContractState | None:
    """Read strict policy and baseline blobs from one exact historical commit."""

    root = repo_root.resolve()
    commit = resolve_base_commit(root, base_ref)
    entries = _contract_tree_entries(root, commit)
    present = frozenset(entries)
    if not present:
        return None
    _require(present == frozenset(CONTRACT_PATHS), "historical contract state is partial")
    for path, (mode, object_type) in entries.items():
        _require(
            mode in REGULAR_BLOB_MODES and object_type == "blob",
            f"historical contract path is not a regular blob: {path}",
        )
    policy_text = _read_contract_blob(root, commit, POLICY_PATH, label="policy")
    baseline_text = _read_contract_blob(root, commit, BASELINE_PATH, label="baseline")
    policy = _parse_policy_blob(policy_text, commit)
    baseline = _parse_baseline_blob(baseline_text, commit)
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
        return _read_path_changes(command, repo_root.resolve())
    except GIT_READ_ERRORS as exc:
        raise GitContractError(f"could not read Git path changes for {base_commit}") from exc


def _read_path_changes(command: tuple[str, ...], repo_root: Path) -> tuple[GitPathChange, ...]:
    output = run_git(command, cwd=repo_root, max_bytes=MAX_DIFF_OUTPUT)
    return parse_name_status(output)


def run_git(command: tuple[str, ...], *, cwd: Path, max_bytes: int) -> bytes:
    """Run one argv-only Git command with bounded stdout and no stderr echo."""

    try:
        return command_run.run_command_bytes_bounded(
            list(command),
            cwd=cwd,
            timeout_seconds=GIT_TIMEOUT_SECONDS,
            output_limit_bytes=max_bytes,
        )
    except command_run.CommandRunError as exc:
        raise GitContractError("Git command failed safely") from exc


def _validate_base_ref(base_ref: str) -> None:
    if not SAFE_REF.fullmatch(base_ref):
        raise GitContractError("base ref must be one bounded revision name")
    unsafe_segments = (
        ".." in base_ref
        or "//" in base_ref
        or base_ref.endswith(("/", ".", ".lock"))
        or "/." in base_ref
    )
    if unsafe_segments:
        raise GitContractError("base ref must be one bounded revision name")


def _contract_tree_entries(repo_root: Path, commit: str) -> dict[str, tuple[str, str]]:
    command = (_git(), "ls-tree", "-z", commit, "--", *CONTRACT_PATHS)
    try:
        return _read_tree_entries(command, repo_root)
    except GIT_READ_ERRORS as exc:
        raise GitContractError(f"could not inspect historical contract paths at {commit}") from exc


def _read_tree_entries(command: tuple[str, ...], repo_root: Path) -> dict[str, tuple[str, str]]:
    output = run_git(command, cwd=repo_root, max_bytes=MAX_TREE_OUTPUT)
    return _parse_tree(output)


def _parse_policy_blob(text: str, commit: str) -> ContractPolicy:
    try:
        return parse_policy(text, source=f"{commit}:{POLICY_PATH}")
    except PolicyError as exc:
        raise GitContractError(f"historical contract policy is invalid: {POLICY_PATH}") from exc


def _parse_baseline_blob(text: str, commit: str) -> ContractBaseline:
    try:
        return parse_baseline(text, source=f"{commit}:{BASELINE_PATH}")
    except BaselineError as exc:
        raise GitContractError(f"historical contract baseline is invalid: {BASELINE_PATH}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GitContractError(message)


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
    except (OSError, GitContractError) as exc:
        raise GitContractError(f"could not read historical contract {label}: {path}") from exc
    if len(output) > MAX_INPUT_BYTES:
        raise GitContractError(f"historical contract {label} exceeded the size limit: {path}")
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitContractError(f"historical contract {label} must be UTF-8: {path}") from exc


def _git() -> str:
    return shutil.which("git") or "git"
