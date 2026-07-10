"""Repository path safeguards for DocSync."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from docsync.config.errors import PathBoundaryError
from docsync.config.io import MAX_REPOSITORY_INPUT_BYTES

SENSITIVE_DIRECTORY_NAMES = frozenset(
    (
        ".aws",
        ".azure",
        ".docker",
        ".gcloud",
        ".git",
        ".gnupg",
        ".kube",
        ".ssh",
        ".terraform",
    )
)
SENSITIVE_FILE_NAMES = frozenset(
    (
        ".envrc",
        ".git-credentials",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "application_default_credentials.json",
        "auth.json",
        "credentials.yaml",
        "credentials.yml",
        "credentials",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "kubeconfig",
        "secret.json",
        "secret.yaml",
        "secret.yml",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "service-account.json",
        "service_account.json",
        "token.json",
    )
)
SENSITIVE_SUFFIXES = frozenset(
    (".jks", ".key", ".kdbx", ".keystore", ".ovpn", ".p12", ".pem", ".pfx", ".tfstate")
)
RESERVED_OUTPUT_NAMES = frozenset((".gitignore",))


def resolve_within(root: Path, candidate: Path, *, label: str) -> Path:
    """Resolve a relative path and prove its canonical target remains under ``root``."""

    resolved_root = root.resolve()
    _validate_candidate(candidate, label=label)
    _reject_symlink_components(resolved_root, candidate, label=label)
    return _resolve_descendant(resolved_root, candidate, label=label)


def require_within(root: Path, path: Path, *, label: str) -> Path:
    """Prove an already resolved path remains under ``root``."""

    resolved_root = root.resolve()
    return _require_resolved_descendant(resolved_root, path, label=label)


def require_strict_descendant(root: Path, path: Path, *, label: str) -> Path:
    """Prove ``path`` is contained by, but is not equal to, ``root``."""

    resolved_root = root.resolve()
    resolved_path = require_within(resolved_root, path, label=label)
    if resolved_path == resolved_root:
        raise PathBoundaryError(f"{label} must be a file below {resolved_root}: {path}")
    return resolved_path


def require_unreserved_output(path: Path, *, label: str) -> Path:
    """Reject generated-artifact names owned by DocSync output policy."""

    if path.name.lower() in RESERVED_OUTPUT_NAMES:
        raise PathBoundaryError(f"{label} uses reserved policy filename: {path.name}")
    return path


def resolve_input_within(
    root: Path,
    candidate: Path,
    *,
    label: str,
    allow_missing: bool = False,
    max_bytes: int = MAX_REPOSITORY_INPUT_BYTES,
) -> Path:
    """Resolve a repository input and require a bounded regular file when present."""

    if sensitive_path(candidate):
        raise PathBoundaryError(f"{label} is a sensitive path and cannot be read: {candidate}")
    resolved = resolve_within(root, candidate, label=label)
    if resolved.exists():
        _require_bounded_regular_file(resolved, label=label, max_bytes=max_bytes)
        return resolved
    if allow_missing:
        return resolved
    raise PathBoundaryError(f"{label} does not exist: {candidate}")


def resolve_directory_within(
    root: Path,
    candidate: Path,
    *,
    label: str,
    allow_missing: bool = True,
    reject_sensitive: bool = False,
) -> Path:
    """Resolve a repository directory and require directory type when present."""

    if reject_sensitive and sensitive_path(candidate):
        raise PathBoundaryError(f"{label} is a sensitive path: {candidate}")
    resolved = resolve_within(root, candidate, label=label)
    return _require_directory(resolved, candidate, label=label, allow_missing=allow_missing)


def sensitive_path(path: Path) -> bool:
    """Return whether a path name commonly contains credentials or private keys."""

    lowered_parts = tuple(part.lower() for part in path.parts)
    if any(part in SENSITIVE_DIRECTORY_NAMES for part in lowered_parts):
        return True
    name = path.name.lower()
    if _sensitive_file_name(name):
        return True
    normalized_name = name.replace("-", "_")
    return path.suffix.lower() in SENSITIVE_SUFFIXES or "private_key" in normalized_name


def _validate_candidate(candidate: Path, *, label: str) -> None:
    if candidate.is_absolute():
        raise PathBoundaryError(f"{label} must be relative to the repository: {candidate}")
    if ".." in candidate.parts:
        raise PathBoundaryError(f"{label} must not contain '..': {candidate}")


def _resolve_descendant(root: Path, candidate: Path, *, label: str) -> Path:
    try:
        return _resolved_descendant(root, candidate)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PathBoundaryError(f"{label} resolves outside the approved root: {candidate}") from exc


def _resolved_descendant(root: Path, candidate: Path) -> Path:
    resolved = (root / candidate).resolve()
    resolved.relative_to(root)
    return resolved


def _require_resolved_descendant(root: Path, path: Path, *, label: str) -> Path:
    try:
        return _resolved_path_within(root, path)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PathBoundaryError(f"{label} must remain under {root}: {path}") from exc


def _resolved_path_within(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def _require_directory(
    resolved: Path,
    candidate: Path,
    *,
    label: str,
    allow_missing: bool,
) -> Path:
    if not resolved.exists():
        if allow_missing:
            return resolved
        raise PathBoundaryError(f"{label} does not exist: {candidate}")
    metadata = _path_stat(resolved, label=label)
    if not stat.S_ISDIR(metadata.st_mode):
        raise PathBoundaryError(f"{label} must be a directory: {candidate}")
    return resolved


def _path_stat(path: Path, *, label: str) -> os.stat_result:
    try:
        return path.stat()
    except OSError as exc:
        raise PathBoundaryError(f"Cannot inspect {label}: {path}") from exc


def _require_bounded_regular_file(path: Path, *, label: str, max_bytes: int) -> None:
    metadata = _path_stat(path, label=label)
    if not stat.S_ISREG(metadata.st_mode):
        raise PathBoundaryError(f"{label} must be a regular file: {path}")
    if metadata.st_size > max_bytes:
        raise PathBoundaryError(f"{label} exceeds the {max_bytes}-byte limit: {path}")


def _sensitive_file_name(name: str) -> bool:
    if name == ".env" or name.startswith(".env."):
        return True
    if name in SENSITIVE_FILE_NAMES:
        return True
    if name.startswith("client_secret") and name.endswith(".json"):
        return True
    return name.endswith((".tfvars", ".tfvars.json", ".tfstate.backup"))


def _reject_symlink_components(root: Path, candidate: Path, *, label: str) -> None:
    current = root
    for part in candidate.parts:
        if part in ("", "."):
            continue
        current /= part
        metadata = _component_metadata(current, candidate=candidate, label=label)
        if metadata is None:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise PathBoundaryError(f"{label} must not contain symlinks: {candidate}")


def _component_metadata(
    path: Path,
    *,
    candidate: Path,
    label: str,
) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PathBoundaryError(f"Cannot inspect {label}: {candidate}") from exc
