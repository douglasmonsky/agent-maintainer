"""Symlink-safe filesystem boundary for release distribution bundles."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO, cast

from agent_run_artifacts import distribution_bundle as contract

MAX_MANIFEST_BYTES = 1024 * 1024
COPY_CHUNK_BYTES = 1024 * 1024
OUTPUT_MODE = 0o644
DIRECTORY_MODE = 0o755


def create_distribution_bundle(
    source: Path,
    bundle: Path,
    *,
    expected_sha: str,
) -> contract.DistributionBundleVerification:
    """Atomically copy source packages into a verified distribution bundle."""

    source_artifacts = _source_artifacts(source)
    _require_new_bundle_path(bundle)
    temporary = Path(
        tempfile.mkdtemp(
            dir=bundle.parent,
            prefix=f".{bundle.name}.",
        )
    )
    try:
        return _create_temporary_bundle(
            temporary,
            bundle,
            source_artifacts,
            expected_sha=expected_sha,
        )
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot create distribution bundle {bundle}: {exc}"
        ) from exc
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def _create_temporary_bundle(
    temporary: Path,
    bundle: Path,
    source_artifacts: tuple[Path, ...],
    *,
    expected_sha: str,
) -> contract.DistributionBundleVerification:
    packages = temporary / contract.PACKAGES_DIRECTORY
    packages.mkdir(mode=DIRECTORY_MODE)
    records = tuple(_copy_artifact(path, packages / path.name) for path in source_artifacts)
    payload = contract.create_manifest(records, commit=expected_sha)
    _write_manifest(temporary / contract.MANIFEST_NAME, payload)
    _payload, manifest_sha256 = _read_manifest(temporary / contract.MANIFEST_NAME)
    verified = verify_distribution_bundle(
        temporary,
        expected_sha=expected_sha,
        expected_manifest_sha256=manifest_sha256,
    )
    os.replace(temporary, bundle)
    return verified


def verify_distribution_bundle(
    bundle: Path,
    *,
    expected_sha: str,
    expected_manifest_sha256: str,
) -> contract.DistributionBundleVerification:
    """Verify exact bundle inventory, commit, sizes, and SHA-256 digests."""

    try:
        return _verified_distribution_bundle(
            bundle,
            expected_sha=expected_sha,
            expected_manifest_sha256=expected_manifest_sha256,
        )
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot verify distribution bundle {bundle}: {exc}"
        ) from exc


def _verified_distribution_bundle(
    bundle: Path,
    *,
    expected_sha: str,
    expected_manifest_sha256: str,
) -> contract.DistributionBundleVerification:
    _require_directory(bundle, label="distribution bundle")
    _require_root_inventory(bundle)
    contract.validate_manifest_sha256(expected_manifest_sha256)
    payload, manifest_sha256 = _read_manifest(bundle / contract.MANIFEST_NAME)
    if manifest_sha256 != expected_manifest_sha256:
        raise contract.DistributionBundleError("distribution manifest digest mismatch")
    artifacts = contract.validate_manifest(payload, expected_sha=expected_sha)
    packages = bundle / contract.PACKAGES_DIRECTORY
    _require_directory(packages, label="distribution package directory")
    _verify_inventory(packages, artifacts)
    for artifact in artifacts:
        path = bundle / Path(artifact.path)
        digest = _digest_regular_file(path, expected_size=artifact.size)
        if digest != artifact.sha256:
            raise contract.DistributionBundleError(
                f"distribution artifact digest mismatch: {artifact.path}"
            )
    return contract.DistributionBundleVerification(
        artifacts=artifacts,
        manifest_sha256=manifest_sha256,
    )


def _source_artifacts(source: Path) -> tuple[Path, ...]:
    _require_directory(source, label="distribution source")
    try:
        entries = tuple(sorted(source.iterdir(), key=lambda item: item.name))
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot list distribution source {source}: {exc}"
        ) from exc
    for path in entries:
        _require_regular_file(path, label="distribution source artifact")
        contract.package_path(path.name)
    return entries


def _require_new_bundle_path(bundle: Path) -> None:
    _require_directory(bundle.parent, label="distribution bundle parent")
    try:
        bundle.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot inspect distribution bundle {bundle}: {exc}"
        ) from exc
    raise contract.DistributionBundleError(f"distribution bundle already exists: {bundle}")


def _copy_artifact(
    source: Path,
    destination: Path,
) -> contract.DistributionArtifact:
    digest = hashlib.sha256()
    total = 0
    with _open_regular_binary(source) as source_handle, destination.open("xb") as output:
        initial = _file_identity(source_handle)
        while chunk := source_handle.read(COPY_CHUNK_BYTES):
            total += len(chunk)
            if total > contract.MAX_ARTIFACT_BYTES:
                raise contract.DistributionBundleError(
                    f"distribution artifact exceeds size limit: {source.name}"
                )
            digest.update(chunk)
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())
        _require_unchanged_file(source_handle, source, initial=initial, bytes_read=total)
    os.chmod(destination, OUTPUT_MODE)
    return contract.DistributionArtifact(
        path=contract.package_path(source.name),
        size=total,
        sha256=digest.hexdigest(),
    )


def _read_manifest(path: Path) -> tuple[dict[str, object], str]:
    with _open_regular_binary(path) as handle:
        initial = _file_identity(handle)
        metadata = os.fstat(handle.fileno())
        if metadata.st_size > MAX_MANIFEST_BYTES:
            raise contract.DistributionBundleError(
                f"distribution manifest exceeds byte limit {MAX_MANIFEST_BYTES}"
            )
        raw = handle.read(MAX_MANIFEST_BYTES + 1)
        _require_unchanged_file(handle, path, initial=initial, bytes_read=len(raw))
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise contract.DistributionBundleError(
            f"cannot parse distribution manifest {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise contract.DistributionBundleError("distribution manifest must contain an object")
    return cast(dict[str, object], payload), hashlib.sha256(raw).hexdigest()


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    encoded = f"{json.dumps(payload, indent=2, sort_keys=True)}\n".encode()
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, OUTPUT_MODE)


def _require_root_inventory(bundle: Path) -> None:
    expected = {contract.MANIFEST_NAME, contract.PACKAGES_DIRECTORY}
    try:
        actual = {path.name for path in bundle.iterdir()}
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot list distribution bundle {bundle}: {exc}"
        ) from exc
    if actual != expected:
        raise contract.DistributionBundleError(
            f"distribution bundle root inventory mismatch: {sorted(actual)}"
        )


def _verify_inventory(
    packages: Path,
    artifacts: tuple[contract.DistributionArtifact, ...],
) -> None:
    try:
        actual_paths = tuple(sorted(packages.iterdir(), key=lambda item: item.name))
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot list distribution package directory {packages}: {exc}"
        ) from exc
    actual = {f"{contract.PACKAGES_DIRECTORY}/{path.name}" for path in actual_paths}
    for path in actual_paths:
        _require_regular_file(path, label="distribution artifact")
    expected = {artifact.path for artifact in artifacts}
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        raise contract.DistributionBundleError(f"distribution artifacts missing: {missing}")
    if unexpected:
        raise contract.DistributionBundleError(f"unexpected distribution artifacts: {unexpected}")


def _digest_regular_file(path: Path, *, expected_size: int) -> str:
    digest = hashlib.sha256()
    with _open_regular_binary(path) as handle:
        initial = _file_identity(handle)
        metadata = os.fstat(handle.fileno())
        if metadata.st_size != expected_size:
            raise contract.DistributionBundleError(
                f"distribution artifact size mismatch: {path.name}"
            )
        while chunk := handle.read(COPY_CHUNK_BYTES):
            digest.update(chunk)
        _require_unchanged_file(
            handle,
            path,
            initial=initial,
            bytes_read=expected_size,
        )
    return digest.hexdigest()


def _open_regular_binary(path: Path) -> BinaryIO:
    _require_regular_file(path, label="distribution artifact")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise contract.DistributionBundleError(
            f"cannot open regular distribution file {path}: {exc}"
        ) from exc
    handle = os.fdopen(descriptor, "rb")
    metadata = os.fstat(handle.fileno())
    if not stat.S_ISREG(metadata.st_mode):
        handle.close()
        raise contract.DistributionBundleError(
            f"distribution artifact must be a regular file: {path}"
        )
    return handle


def _require_unchanged_file(
    handle: BinaryIO,
    path: Path,
    *,
    initial: tuple[int, int, int, int, int],
    bytes_read: int,
) -> None:
    current = _file_identity(handle)
    if current != initial or current[2] != bytes_read:
        raise contract.DistributionBundleError(f"distribution file changed while reading: {path}")


def _file_identity(handle: BinaryIO) -> tuple[int, int, int, int, int]:
    metadata = os.fstat(handle.fileno())
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _require_regular_file(path: Path, *, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise contract.DistributionBundleError(f"cannot inspect {label} {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise contract.DistributionBundleError(f"{label} must be a regular file: {path}")
    return metadata


def _require_directory(path: Path, *, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise contract.DistributionBundleError(f"cannot inspect {label} {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise contract.DistributionBundleError(f"{label} must be a regular directory: {path}")
    return metadata
