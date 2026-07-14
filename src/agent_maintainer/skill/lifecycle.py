"""Ownership-safe lifecycle for personal Agent Maintainer skills."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Final, cast

from agent_maintainer.skill import resources
from agent_maintainer.skill.models import (
    SkillBundle,
    SkillManifest,
    SkillState,
    SkillStatus,
)

CLIENTS: Final = ("codex", "claude-code")
MANIFEST_NAME: Final = ".agent-maintainer-skill.json"
SCHEMA_VERSION: Final = 1
CLIENT_PATHS: Final = {
    "codex": Path(".codex/skills/agent-maintainer-setup"),
    "claude-code": Path(".claude/skills/agent-maintainer-setup"),
}


class SkillOwnershipError(RuntimeError):
    """Raised when a lifecycle command would change unowned content."""


class SkillMutationError(RuntimeError):
    """Raised when a staged skill-directory mutation cannot complete."""


def client_destination(home: Path, client: str) -> Path:
    """Return the personal skill directory for one supported client."""

    try:
        relative_path = CLIENT_PATHS[client]
    except KeyError as exc:
        msg = f"Unsupported skill client: {client}"
        raise ValueError(msg) from exc
    return home / relative_path


def status(home: Path, client: str) -> SkillStatus:
    """Return ownership-aware setup skill status for one client."""

    bundle = resources.load_bundle()
    return _status(home, client, bundle=bundle)


def install(home: Path, clients: tuple[str, ...]) -> tuple[SkillStatus, ...]:
    """Install or update the portable setup skill for selected clients."""

    selected = _validated_clients(clients)
    bundle = resources.load_bundle()
    results: list[SkillStatus] = []
    for client in selected:
        before = _status(home, client, bundle=bundle)
        if before.state is SkillState.CURRENT:
            results.append(before)
            continue
        _require_owned_or_missing(before)
        old_files = (
            _read_manifest(before.destination, client=client, bundle=bundle).files
            if before.state is SkillState.STALE
            else ()
        )
        _replace_destination(
            before.destination,
            lambda staged, selected_client=client, owned=old_files: _replace_bundle(
                staged,
                owned,
                client=selected_client,
                bundle=bundle,
            ),
        )
        results.append(_status(home, client, bundle=bundle))
    return tuple(results)


def uninstall(home: Path, clients: tuple[str, ...]) -> tuple[SkillStatus, ...]:
    """Remove only hash-verified files owned by the portable setup skill."""

    selected = _validated_clients(clients)
    bundle = resources.load_bundle()
    results: list[SkillStatus] = []
    for client in selected:
        before = _status(home, client, bundle=bundle)
        if before.state is SkillState.MISSING:
            results.append(before)
            continue
        _require_owned(before)
        manifest = _read_manifest(before.destination, client=client, bundle=bundle)
        _replace_destination(
            before.destination,
            lambda staged, owned=manifest.files: _remove_bundle(staged, owned),
        )
        _remove_empty_directory(before.destination)
        results.append(_status(home, client, bundle=bundle))
    return tuple(results)


def _status(home: Path, client: str, *, bundle: SkillBundle) -> SkillStatus:
    destination = client_destination(home, client)
    if destination.is_symlink():
        return _modified_status(
            destination,
            client,
            bundle,
            "destination is not an owned directory",
        )
    if not destination.exists():
        return _missing_status(home, client, bundle=bundle)
    if not destination.is_dir():
        return _modified_status(
            destination,
            client,
            bundle,
            "destination is not an owned directory",
        )
    try:
        manifest = _read_manifest(destination, client=client, bundle=bundle)
    except SkillOwnershipError as exc:
        return _modified_status(destination, client, bundle, str(exc))
    problem = _managed_content_problem(destination, manifest)
    if problem:
        return _modified_status(destination, client, bundle, problem)
    packaged_files = tuple(sorted((item.relative_path, item.digest) for item in bundle.files))
    state = (
        SkillState.CURRENT
        if manifest.package_version == bundle.package_version and manifest.files == packaged_files
        else SkillState.STALE
    )
    return SkillStatus(
        client,
        destination,
        state,
        bundle.package_version,
        manifest.package_version,
    )


def _missing_status(home: Path, client: str, *, bundle: SkillBundle) -> SkillStatus:
    return SkillStatus(
        client,
        client_destination(home, client),
        SkillState.MISSING,
        bundle.package_version,
    )


def _modified_status(
    destination: Path,
    client: str,
    bundle: SkillBundle,
    detail: str,
) -> SkillStatus:
    return SkillStatus(
        client,
        destination,
        SkillState.LOCALLY_MODIFIED,
        bundle.package_version,
        detail=detail,
    )


def _read_manifest(destination: Path, *, client: str, bundle: SkillBundle) -> SkillManifest:
    manifest_path = destination / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        msg = "ownership manifest is missing or unsafe"
        raise SkillOwnershipError(msg)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = _parse_manifest(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        msg = f"ownership manifest is invalid: {exc}"
        raise SkillOwnershipError(msg) from exc
    if manifest.schema_version != SCHEMA_VERSION or manifest.skill != bundle.name:
        msg = "ownership manifest identity mismatch"
        raise SkillOwnershipError(msg)
    if manifest.client != client:
        msg = "ownership manifest client mismatch"
        raise SkillOwnershipError(msg)
    return manifest


def _parse_manifest(payload: object) -> SkillManifest:
    if not isinstance(payload, dict):
        raise TypeError("root must be an object")
    manifest_data = cast("dict[str, object]", payload)
    parsed_files = _parse_manifest_files(manifest_data.get("files"))
    schema_version = manifest_data.get("schema_version")
    if not isinstance(schema_version, int):
        raise TypeError("schema_version must be an integer")
    return SkillManifest(
        schema_version,
        _required_string(manifest_data, "skill"),
        _required_string(manifest_data, "client"),
        _required_string(manifest_data, "package_version"),
        tuple(sorted(parsed_files)),
    )


def _parse_manifest_files(value: object) -> list[tuple[str, str]]:
    if not isinstance(value, dict):
        raise TypeError("files must map paths to digests")
    parsed: list[tuple[str, str]] = []
    for path, digest in cast("dict[object, object]", value).items():
        if not isinstance(path, str) or not isinstance(digest, str):
            raise TypeError("files must map paths to digests")
        _validate_managed_path(path)
        parsed.append((path, digest))
    return parsed


def _validate_managed_path(path: str) -> None:
    parsed = PurePosixPath(path)
    if (
        not path
        or parsed.is_absolute()
        or parsed.as_posix() != path
        or any(part in {".", ".."} for part in parsed.parts)
        or path == MANIFEST_NAME
    ):
        raise TypeError("files must use safe relative paths")


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise TypeError("skill, client, and package_version must be non-empty strings")
    return value


def _managed_content_problem(destination: Path, manifest: SkillManifest) -> str:
    for relative_path, expected_digest in manifest.files:
        if _managed_path_has_symlink(destination, relative_path):
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


def _write_bundle(destination: Path, *, client: str, bundle: SkillBundle) -> None:
    for item in bundle.files:
        _validate_managed_path(item.relative_path)
        if _managed_path_has_symlink(destination, item.relative_path):
            msg = f"unsafe managed path: {item.relative_path}"
            raise SkillOwnershipError(msg)
        path = destination.joinpath(*item.relative_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item.content, encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "skill": bundle.name,
        "client": client,
        "package_version": bundle.package_version,
        "files": {item.relative_path: item.digest for item in bundle.files},
    }
    _write_json(destination / MANIFEST_NAME, manifest)


def _managed_path_has_symlink(destination: Path, relative_path: str) -> bool:
    current = destination
    for part in PurePosixPath(relative_path).parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def _replace_bundle(
    destination: Path,
    old_files: tuple[tuple[str, str], ...],
    *,
    client: str,
    bundle: SkillBundle,
) -> None:
    if old_files:
        _remove_bundle(destination, old_files)
    _write_bundle(destination, client=client, bundle=bundle)


def _remove_bundle(destination: Path, files: tuple[tuple[str, str], ...]) -> None:
    for relative_path, _digest in files:
        path = destination.joinpath(*relative_path.split("/"))
        path.unlink()
        _prune_empty_parents(path.parent, stop=destination)
    (destination / MANIFEST_NAME).unlink()


def _replace_destination(destination: Path, mutation: Callable[[Path], None]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.stage-",
            dir=destination.parent,
        )
    )
    backup: Path | None = None
    try:
        if destination.exists():
            shutil.copytree(destination, staged, dirs_exist_ok=True, symlinks=True)
        mutation(staged)
        if not destination.exists():
            os.replace(staged, destination)
            return
        backup = destination.parent / f".{destination.name}.backup-{uuid.uuid4().hex}"
        os.replace(destination, backup)
        try:
            os.replace(staged, destination)
        except OSError as exc:
            _restore_backup(backup, destination, cause=exc)
        shutil.rmtree(backup)
    except SkillMutationError:
        raise
    except OSError as exc:
        msg = f"skill mutation failed before replacement: {exc}"
        raise SkillMutationError(msg) from exc
    finally:
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)


def _restore_backup(backup: Path, destination: Path, *, cause: OSError) -> None:
    try:
        os.replace(backup, destination)
    except OSError as rollback_error:
        msg = f"skill mutation failed; rollback incomplete ({rollback_error}): {cause}"
        raise SkillMutationError(msg) from cause
    msg = f"skill mutation failed and was rolled back: {cause}"
    raise SkillMutationError(msg) from cause


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _validated_clients(clients: tuple[str, ...]) -> tuple[str, ...]:
    if not clients:
        raise ValueError("At least one skill client is required")
    selected: list[str] = []
    for client in clients:
        client_destination(Path(), client)
        if client not in selected:
            selected.append(client)
    return tuple(selected)


def _require_owned_or_missing(status_value: SkillStatus) -> None:
    if status_value.state is SkillState.LOCALLY_MODIFIED:
        msg = f"{status_value.client} skill is locally modified: {status_value.detail}"
        raise SkillOwnershipError(msg)


def _require_owned(status_value: SkillStatus) -> None:
    if status_value.state not in {SkillState.CURRENT, SkillState.STALE}:
        msg = f"{status_value.client} skill is locally modified: {status_value.detail}"
        raise SkillOwnershipError(msg)


def _prune_empty_parents(path: Path, *, stop: Path) -> None:
    current = path
    while current != stop:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _remove_empty_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        return
