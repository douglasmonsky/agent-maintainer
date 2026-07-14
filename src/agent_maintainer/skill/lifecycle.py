"""Ownership-safe lifecycle for personal Agent Maintainer skills."""

from __future__ import annotations

from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import Final

from agent_maintainer.skill import ownership, resources, transactions
from agent_maintainer.skill.models import (
    SkillBundle,
    SkillManifest,
    SkillState,
    SkillStatus,
)

CLIENTS: Final = ("codex", "claude-code")
MANIFEST_NAME: Final = ownership.MANIFEST_NAME
SCHEMA_VERSION: Final = ownership.SCHEMA_VERSION


SkillOwnershipError = ownership.ManifestOwnershipError


SkillMutationError = transactions.SkillMutationError


def client_destination(home: Path, client: str) -> Path:
    """Return the personal skill directory for one supported client."""

    if client == "codex":
        relative_path = Path(".codex/skills/agent-maintainer-setup")
    elif client == "claude-code":
        relative_path = Path(".claude/skills/agent-maintainer-setup")
    else:
        raise ValueError(f"Unsupported skill client: {client}")
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
        mutation = partial(_replace_bundle, old_files=old_files, client=client, bundle=bundle)
        transactions.replace_destination(before.destination, mutation)
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
        mutation = partial(_remove_bundle, files=manifest.files)
        transactions.replace_destination(before.destination, mutation)
        _remove_empty_directory(before.destination)
        results.append(_status(home, client, bundle=bundle))
    return tuple(results)


def _status(home: Path, client: str, *, bundle: SkillBundle) -> SkillStatus:
    destination = client_destination(home, client)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        return _modified_status(
            destination,
            client,
            bundle,
            "destination is not an owned directory",
        )
    if not destination.exists():
        return _missing_status(home, client, bundle=bundle)
    try:
        manifest = _read_manifest(destination, client=client, bundle=bundle)
    except SkillOwnershipError as exc:
        return _modified_status(destination, client, bundle, str(exc))
    problem = ownership.managed_content_problem(destination, manifest)
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
    return ownership.read_manifest(destination, client=client, skill_name=bundle.name)


def _write_bundle(destination: Path, *, client: str, bundle: SkillBundle) -> None:
    for bundle_file in bundle.files:
        ownership.validate_managed_path(bundle_file.relative_path)
        if ownership.managed_path_has_symlink(destination, bundle_file.relative_path):
            msg = f"unsafe managed path: {bundle_file.relative_path}"
            raise SkillOwnershipError(msg)
        path = destination.joinpath(*bundle_file.relative_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(bundle_file.content, encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "skill": bundle.name,
        "client": client,
        "package_version": bundle.package_version,
        "files": {item.relative_path: item.digest for item in bundle.files},
    }
    ownership.write_manifest(destination / MANIFEST_NAME, manifest)


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
    with suppress(OSError):
        path.rmdir()
