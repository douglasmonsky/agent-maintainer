"""Trust contract for exact-commit Python distribution bundles."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import cast

BUNDLE_VERSION = 1
BUNDLE_KIND = "agent-maintainer-distribution-bundle"
PACKAGES_DIRECTORY = "packages"
MANIFEST_NAME = "manifest.json"
MAX_ARTIFACTS = 32
MAX_ARTIFACT_BYTES = 1024 * 1024 * 1024
PACKAGE_PATH_PARTS = 2
FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
FULL_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,254}\Z")
MANIFEST_FIELDS = frozenset(("version", "kind", "commit", "files"))
ARTIFACT_FIELDS = frozenset(("path", "size", "sha256"))


class DistributionBundleError(ValueError):
    """Raised when a distribution bundle fails its trust contract."""


@dataclass(frozen=True)
class DistributionArtifact:
    """One immutable package record from a distribution manifest."""

    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class DistributionBundleVerification:
    """Trusted manifest identity and its exact package records."""

    artifacts: tuple[DistributionArtifact, ...]
    manifest_sha256: str


def create_manifest(
    artifacts: Sequence[DistributionArtifact],
    *,
    commit: str,
) -> dict[str, object]:
    """Return a validated deterministic manifest payload."""

    payload: dict[str, object] = {
        "version": BUNDLE_VERSION,
        "kind": BUNDLE_KIND,
        "commit": commit,
        "files": [
            {
                "path": artifact.path,
                "size": artifact.size,
                "sha256": artifact.sha256,
            }
            for artifact in artifacts
        ],
    }
    validate_manifest(payload, expected_sha=commit)
    return payload


def validate_manifest(
    payload: Mapping[str, object],
    *,
    expected_sha: str,
) -> tuple[DistributionArtifact, ...]:
    """Validate a bundle manifest and return its trusted package records."""

    _validate_sha(expected_sha, label="expected commit")
    _require_fields(payload, MANIFEST_FIELDS, label="distribution manifest")
    if payload.get("version") != BUNDLE_VERSION:
        raise DistributionBundleError("unsupported distribution manifest version")
    if payload.get("kind") != BUNDLE_KIND:
        raise DistributionBundleError("unexpected distribution manifest kind")
    commit = _required_text(payload.get("commit"), "distribution manifest commit")
    _validate_sha(commit, label="distribution manifest commit")
    if commit != expected_sha:
        raise DistributionBundleError("distribution manifest does not match expected commit")
    artifacts = _artifact_entries(payload.get("files"))
    _validate_inventory(artifacts)
    return artifacts


def package_path(filename: str) -> str:
    """Return the canonical bundle-relative path for one package filename."""

    if SAFE_FILENAME.fullmatch(filename) is None:
        raise DistributionBundleError(f"unsafe package filename: {filename!r}")
    path = f"{PACKAGES_DIRECTORY}/{filename}"
    _package_kind(path)
    return path


def validate_manifest_sha256(value: str) -> None:
    """Require one full lowercase SHA-256 manifest identity."""

    if FULL_SHA256.fullmatch(value) is None:
        raise DistributionBundleError("expected manifest SHA-256 is malformed")


def _artifact_entries(value: object) -> tuple[DistributionArtifact, ...]:
    if not isinstance(value, list):
        raise DistributionBundleError("distribution manifest files must be an array")
    entries = cast(list[object], value)
    if not entries or len(entries) > MAX_ARTIFACTS:
        raise DistributionBundleError(f"distribution manifest must contain 1-{MAX_ARTIFACTS} files")
    return tuple(_artifact_entry(item, index=index) for index, item in enumerate(entries))


def _artifact_entry(value: object, *, index: int) -> DistributionArtifact:
    if not isinstance(value, dict):
        raise DistributionBundleError(f"distribution file {index} must be an object")
    entry = cast(dict[str, object], value)
    _require_fields(entry, ARTIFACT_FIELDS, label=f"distribution file {index}")
    path = _required_text(entry.get("path"), f"distribution file {index} path")
    _validate_package_path(path)
    size = _artifact_size(entry.get("size"), path=path)
    digest = _artifact_digest(entry.get("sha256"), path=path)
    return DistributionArtifact(path=path, size=size, sha256=digest)


def _artifact_size(value: object, *, path: str) -> int:
    size = value
    if isinstance(size, bool) or not isinstance(size, int):
        raise DistributionBundleError(f"distribution file {path} size must be an integer")
    if size <= 0 or size > MAX_ARTIFACT_BYTES:
        raise DistributionBundleError(
            f"distribution file {path} size must be between 1 and {MAX_ARTIFACT_BYTES}"
        )
    return size


def _artifact_digest(value: object, *, path: str) -> str:
    digest = _required_text(value, f"distribution file {path} sha256")
    if FULL_SHA256.fullmatch(digest) is None:
        raise DistributionBundleError(f"distribution file {path} sha256 is malformed")
    return digest


def _validate_inventory(artifacts: tuple[DistributionArtifact, ...]) -> None:
    paths = tuple(artifact.path for artifact in artifacts)
    if paths != tuple(sorted(paths)):
        raise DistributionBundleError("distribution manifest files must be sorted by path")
    if len(set(paths)) != len(paths):
        raise DistributionBundleError("distribution manifest contains duplicate paths")
    package_kinds = {_package_kind(path) for path in paths}
    if not {"wheel", "sdist"}.issubset(package_kinds):
        raise DistributionBundleError("distribution bundle requires a wheel and sdist")


def _validate_package_path(path: str) -> None:
    parsed = PurePosixPath(path)
    if (
        "\\" in path
        or parsed.is_absolute()
        or len(parsed.parts) != PACKAGE_PATH_PARTS
        or parsed.parts[0] != PACKAGES_DIRECTORY
    ):
        raise DistributionBundleError(f"unsafe path in distribution manifest: {path!r}")
    if package_path(parsed.name) != path:
        raise DistributionBundleError(f"unsafe path in distribution manifest: {path!r}")


def _package_kind(path: str) -> str:
    if path.endswith(".whl"):
        return "wheel"
    if path.endswith(".tar.gz"):
        return "sdist"
    raise DistributionBundleError(f"unsupported distribution artifact: {path}")


def _require_fields(
    value: Mapping[str, object],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise DistributionBundleError(
            f"{label} fields are invalid (missing={missing}, extra={extra})"
        )


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DistributionBundleError(f"{label} must be a non-empty string")
    return value


def _validate_sha(value: str, *, label: str) -> None:
    if FULL_GIT_SHA.fullmatch(value) is None:
        raise DistributionBundleError(f"{label} must be a full lowercase Git SHA")
