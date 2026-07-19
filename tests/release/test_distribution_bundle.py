"""Tests for immutable release distribution bundles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer import release_artifacts_io
from agent_run_artifacts import distribution_bundle

GIT_SHA_LENGTH = 40
COMMIT_SHA = "c" * GIT_SHA_LENGTH
OTHER_SHA = "d" * GIT_SHA_LENGTH
WHEEL_NAME = "agent_maintainer-0.1.0b13-py3-none-any.whl"
SDIST_NAME = "agent_maintainer-0.1.0b13.tar.gz"
PACKAGES_DIR = "packages"


def source_distributions(root: Path) -> Path:
    """Create one synthetic wheel/sdist source directory."""

    source = root / "dist"
    source.mkdir()
    (source / WHEEL_NAME).write_bytes(b"wheel-bytes")
    (source / SDIST_NAME).write_bytes(b"sdist-bytes")
    return source


def created_bundle(root: Path) -> Path:
    """Create and return one valid synthetic distribution bundle."""

    source = source_distributions(root)
    bundle = root / "bundle"
    release_artifacts_io.create_distribution_bundle(
        source,
        bundle,
        expected_sha=COMMIT_SHA,
    )
    return bundle


def manifest_payload(bundle: Path) -> dict[str, object]:
    """Read one test bundle manifest."""

    payload = cast(
        object,
        json.loads((bundle / "manifest.json").read_text(encoding="utf-8")),
    )
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def manifest_sha256(bundle: Path) -> str:
    """Return the independently carried identity of one test manifest."""

    return hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()


def test_create_and_verify_distribution_bundle(tmp_path: Path) -> None:
    """Creation emits deterministic, exact-commit package evidence."""

    bundle = created_bundle(tmp_path)

    verified = release_artifacts_io.verify_distribution_bundle(
        bundle,
        expected_sha=COMMIT_SHA,
        expected_manifest_sha256=manifest_sha256(bundle),
    )
    payload = manifest_payload(bundle)

    assert payload["version"] == 1
    assert payload["kind"] == "agent-maintainer-distribution-bundle"
    assert payload["commit"] == COMMIT_SHA
    assert [artifact.path for artifact in verified.artifacts] == [
        f"packages/{WHEEL_NAME}",
        f"packages/{SDIST_NAME}",
    ]
    assert sorted((bundle / PACKAGES_DIR).iterdir()) == [
        bundle / PACKAGES_DIR / WHEEL_NAME,
        bundle / PACKAGES_DIR / SDIST_NAME,
    ]


def test_create_manifest_is_deterministic(tmp_path: Path) -> None:
    """Identical package bytes and commit produce identical manifests."""

    source = source_distributions(tmp_path)
    first = tmp_path / "first-bundle"
    second = tmp_path / "second-bundle"
    release_artifacts_io.create_distribution_bundle(
        source,
        first,
        expected_sha=COMMIT_SHA,
    )
    release_artifacts_io.create_distribution_bundle(
        source,
        second,
        expected_sha=COMMIT_SHA,
    )

    assert (first / "manifest.json").read_bytes() == (second / "manifest.json").read_bytes()
    with pytest.raises(distribution_bundle.DistributionBundleError, match="already exists"):
        release_artifacts_io.create_distribution_bundle(
            source,
            first,
            expected_sha=COMMIT_SHA,
        )


@pytest.mark.parametrize("missing_name", (WHEEL_NAME, SDIST_NAME))
def test_create_requires_wheel_and_sdist(tmp_path: Path, missing_name: str) -> None:
    """A release bundle is incomplete without both package formats."""

    source = source_distributions(tmp_path)
    (source / missing_name).unlink()
    bundle = tmp_path / "bundle"

    with pytest.raises(distribution_bundle.DistributionBundleError, match="wheel and sdist"):
        release_artifacts_io.create_distribution_bundle(
            source,
            bundle,
            expected_sha=COMMIT_SHA,
        )

    assert not bundle.exists()


def test_create_rejects_unsupported_source_entry(tmp_path: Path) -> None:
    """Unexpected source bytes cannot silently enter or bypass the bundle."""

    source = source_distributions(tmp_path)
    (source / "checksums.txt").write_text("untrusted", encoding="utf-8")

    with pytest.raises(distribution_bundle.DistributionBundleError, match="unsupported"):
        release_artifacts_io.create_distribution_bundle(
            source,
            tmp_path / "bundle",
            expected_sha=COMMIT_SHA,
        )


def test_create_rejects_symlinked_source_artifact(tmp_path: Path) -> None:
    """Creation never follows a package symlink."""

    source = source_distributions(tmp_path)
    wheel = source / WHEEL_NAME
    wheel.unlink()
    wheel.symlink_to(tmp_path / "outside.whl")

    with pytest.raises(distribution_bundle.DistributionBundleError, match="regular file"):
        release_artifacts_io.create_distribution_bundle(
            source,
            tmp_path / "bundle",
            expected_sha=COMMIT_SHA,
        )


def test_verify_rejects_wrong_commit(tmp_path: Path) -> None:
    """Bundle evidence is unusable for any other checkout."""

    bundle = created_bundle(tmp_path)

    with pytest.raises(distribution_bundle.DistributionBundleError, match="expected commit"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=OTHER_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


def test_verify_rejects_missing_artifact(tmp_path: Path) -> None:
    """A dropped package fails the exact bundle inventory."""

    bundle = created_bundle(tmp_path)
    (bundle / PACKAGES_DIR / WHEEL_NAME).unlink()

    with pytest.raises(distribution_bundle.DistributionBundleError, match="missing"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


def test_verify_rejects_extra_artifact(tmp_path: Path) -> None:
    """An unmanifested package fails the exact bundle inventory."""

    bundle = created_bundle(tmp_path)
    (bundle / PACKAGES_DIR / "substituted.whl").write_bytes(b"substituted")

    with pytest.raises(distribution_bundle.DistributionBundleError, match="unexpected"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


def test_verify_rejects_extra_root_entry(tmp_path: Path) -> None:
    """The bundle root contains only its manifest and package directory."""

    bundle = created_bundle(tmp_path)
    (bundle / "untrusted.txt").write_text("untrusted", encoding="utf-8")

    with pytest.raises(distribution_bundle.DistributionBundleError, match="root inventory"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


@pytest.mark.parametrize(
    ("rewrite_manifest", "error"),
    (
        (False, "artifact digest mismatch"),
        (True, "manifest digest mismatch"),
    ),
)
def test_verify_rejects_same_size_substitution(
    tmp_path: Path,
    rewrite_manifest: bool,
    error: str,
) -> None:
    """Package-only and package-plus-manifest substitution both fail."""

    bundle = created_bundle(tmp_path)
    trusted_manifest_sha256 = manifest_sha256(bundle)
    wheel = bundle / PACKAGES_DIR / WHEEL_NAME
    substituted = b"x" * len(b"wheel-bytes")
    wheel.write_bytes(substituted)
    if rewrite_manifest:
        payload = manifest_payload(bundle)
        raw_files = payload["files"]
        assert isinstance(raw_files, list)
        files = cast(list[dict[str, object]], raw_files)
        wheel_record = next(item for item in files if item["path"] == f"packages/{WHEEL_NAME}")
        wheel_record["sha256"] = hashlib.sha256(substituted).hexdigest()
        (bundle / "manifest.json").write_text(
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )

    with pytest.raises(distribution_bundle.DistributionBundleError, match=error):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=trusted_manifest_sha256,
        )


def test_verify_rejects_size_mismatch(tmp_path: Path) -> None:
    """Changed artifact length fails its manifest record."""

    bundle = created_bundle(tmp_path)
    (bundle / PACKAGES_DIR / SDIST_NAME).write_bytes(b"longer-sdist-bytes")

    with pytest.raises(distribution_bundle.DistributionBundleError, match="size mismatch"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


def test_verify_rejects_symlinked_artifact(tmp_path: Path) -> None:
    """Verification never follows a transferred package symlink."""

    bundle = created_bundle(tmp_path)
    wheel = bundle / PACKAGES_DIR / WHEEL_NAME
    wheel.unlink()
    outside = tmp_path / "outside.whl"
    outside.write_bytes(b"wheel-bytes")
    wheel.symlink_to(outside)

    with pytest.raises(distribution_bundle.DistributionBundleError, match="regular file"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


def test_verify_rejects_symlinked_manifest(tmp_path: Path) -> None:
    """Verification never follows a transferred manifest symlink."""

    bundle = created_bundle(tmp_path)
    manifest = bundle / "manifest.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(manifest.read_bytes())
    manifest.unlink()
    manifest.symlink_to(outside)

    with pytest.raises(distribution_bundle.DistributionBundleError, match="regular file"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


def test_verify_rejects_unsafe_manifest_path(tmp_path: Path) -> None:
    """Manifest-controlled paths stay inside the package directory."""

    bundle = created_bundle(tmp_path)
    payload = manifest_payload(bundle)
    raw_files = payload["files"]
    assert isinstance(raw_files, list)
    files = cast(list[dict[str, object]], raw_files)
    files[0]["path"] = "../outside.whl"
    (bundle / "manifest.json").write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )

    with pytest.raises(distribution_bundle.DistributionBundleError, match="unsafe path"):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


@pytest.mark.parametrize("failure", ("duplicate", "unsorted"))
def test_verify_rejects_ambiguous_inventory(tmp_path: Path, failure: str) -> None:
    """Duplicate or reordered manifest inventories fail closed."""

    bundle = created_bundle(tmp_path)
    payload = manifest_payload(bundle)
    raw_files = payload["files"]
    assert isinstance(raw_files, list)
    files = cast(list[dict[str, object]], raw_files)
    if failure == "duplicate":
        files[1] = dict(files[0])
    else:
        files.reverse()
    (bundle / "manifest.json").write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )

    with pytest.raises(distribution_bundle.DistributionBundleError):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=manifest_sha256(bundle),
        )


@pytest.mark.parametrize(
    ("mutation", "value"),
    (
        ("version", 99),
        ("kind", "other-kind"),
        ("extra", "untrusted"),
        ("raw-json", "{"),
        ("manifest-digest", "not-a-sha256"),
    ),
)
def test_verify_rejects_malformed_contract(
    tmp_path: Path,
    mutation: str,
    value: object,
) -> None:
    """Unknown schemas and fields fail closed."""

    bundle = created_bundle(tmp_path)
    payload = manifest_payload(bundle)
    if mutation == "raw-json":
        assert isinstance(value, str)
        (bundle / "manifest.json").write_text(value, encoding="utf-8")
    elif mutation != "manifest-digest":
        payload[mutation] = value
        (bundle / "manifest.json").write_text(
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )
    expected_manifest_sha256 = value if mutation == "manifest-digest" else manifest_sha256(bundle)
    assert isinstance(expected_manifest_sha256, str)

    with pytest.raises(distribution_bundle.DistributionBundleError):
        release_artifacts_io.verify_distribution_bundle(
            bundle,
            expected_sha=COMMIT_SHA,
            expected_manifest_sha256=expected_manifest_sha256,
        )
