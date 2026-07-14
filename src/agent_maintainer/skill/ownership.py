"""Ownership manifest parsing and managed-content verification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Final, cast

from agent_maintainer.skill.models import SkillManifest

MANIFEST_NAME: Final = ".agent-maintainer-skill.json"
SCHEMA_VERSION: Final = 1


class ManifestOwnershipError(RuntimeError):
    """Raised when a manifest cannot prove managed-file ownership."""


def read_manifest(destination: Path, *, client: str, skill_name: str) -> SkillManifest:
    """Read and validate one client-specific ownership manifest."""
    manifest_path = destination / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ManifestOwnershipError("ownership manifest is missing or unsafe")
    manifest = _load_manifest(manifest_path)
    _validate_identity(manifest, client=client, skill_name=skill_name)
    return manifest


def managed_content_problem(destination: Path, manifest: SkillManifest) -> str:
    """Return the first unsafe or modified managed path, if any."""
    for relative_path, expected_digest in manifest.files:
        if managed_path_has_symlink(destination, relative_path):
            return f"unsafe managed path: {relative_path}"
        path = destination.joinpath(*relative_path.split("/"))
        if path.is_symlink() or not path.is_file():
            return f"missing managed file: {relative_path}"
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            return f"cannot read managed file {relative_path}: {exc}"
        if digest != expected_digest:
            return f"locally modified managed file: {relative_path}"
    return ""


def validate_managed_path(path: str) -> None:
    """Require a canonical relative POSIX path inside the skill directory."""
    parsed = PurePosixPath(path)
    unsafe = (
        not path,
        parsed.is_absolute(),
        parsed.as_posix() != path,
        "." in parsed.parts,
        ".." in parsed.parts,
        path == MANIFEST_NAME,
    )
    if any(unsafe):
        raise TypeError("files must use safe relative paths")


def managed_path_has_symlink(destination: Path, relative_path: str) -> bool:
    """Return whether any existing component redirects through a symlink."""
    current = destination
    for part in PurePosixPath(relative_path).parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def write_manifest(path: Path, payload: Mapping[str, object]) -> None:
    """Write deterministic ownership metadata."""
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(f"{rendered}\n", encoding="utf-8")


def _load_manifest(path: Path) -> SkillManifest:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ManifestOwnershipError(f"ownership manifest is invalid: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestOwnershipError(f"ownership manifest is invalid: {exc}") from exc
    try:
        return _parse_manifest(payload)
    except (TypeError, ValueError) as exc:
        raise ManifestOwnershipError(f"ownership manifest is invalid: {exc}") from exc


def _validate_identity(manifest: SkillManifest, *, client: str, skill_name: str) -> None:
    if manifest.schema_version != SCHEMA_VERSION or manifest.skill != skill_name:
        raise ManifestOwnershipError("ownership manifest identity mismatch")
    if manifest.client != client:
        raise ManifestOwnershipError("ownership manifest client mismatch")


def _parse_manifest(payload: object) -> SkillManifest:
    if not isinstance(payload, dict):
        raise TypeError("root must be an object")
    manifest_data = cast("dict[str, object]", payload)
    schema_version = manifest_data.get("schema_version")
    if not isinstance(schema_version, int):
        raise TypeError("schema_version must be an integer")
    return SkillManifest(
        schema_version,
        _required_string(manifest_data, "skill"),
        _required_string(manifest_data, "client"),
        _required_string(manifest_data, "package_version"),
        tuple(sorted(_parse_manifest_files(manifest_data.get("files")))),
    )


def _parse_manifest_files(value: object) -> list[tuple[str, str]]:
    if not isinstance(value, dict):
        raise TypeError("files must map paths to digests")
    parsed: list[tuple[str, str]] = []
    for path, digest in cast("dict[object, object]", value).items():
        if not isinstance(path, str) or not isinstance(digest, str):
            raise TypeError("files must map paths to digests")
        validate_managed_path(path)
        parsed.append((path, digest))
    return parsed


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise TypeError("skill, client, and package_version must be non-empty strings")
    return value
