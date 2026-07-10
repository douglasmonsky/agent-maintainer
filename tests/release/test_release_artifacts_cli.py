"""Tests for the release-distribution bundle command boundary."""

from __future__ import annotations

import hashlib
from functools import partial
from pathlib import Path

import pytest

from agent_maintainer import release_artifacts as cli

GIT_SHA_LENGTH = 40
COMMIT_SHA = "c" * GIT_SHA_LENGTH
ERROR_EXIT = 2


def source_distributions(root: Path) -> Path:
    """Create synthetic wheel and sdist inputs."""

    source = root / "dist"
    source.mkdir()
    (source / "package-1-py3-none-any.whl").write_bytes(b"wheel")
    (source / "package-1.tar.gz").write_bytes(b"sdist")
    return source


def clean_git_state(_root: Path) -> dict[str, object]:
    """Return the clean commit shared by CLI tests."""

    return {"sha": COMMIT_SHA, "branch": "main", "dirty": False}


def selected_git_state(
    _root: Path,
    *,
    payload: dict[str, object],
) -> dict[str, object]:
    """Return one selected Git state payload."""

    return payload


def test_create_and_verify_cli_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI builds and revalidates one exact-commit bundle."""

    monkeypatch.setattr(cli.git_state, "git_state", clean_git_state)
    source = source_distributions(tmp_path)
    bundle = tmp_path / "bundle"

    assert (
        cli.main(
            [
                "create",
                "--source",
                str(source),
                "--bundle",
                str(bundle),
                "--expected-sha",
                COMMIT_SHA,
            ]
        )
        == 0
    )
    manifest_sha256 = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    assert (
        cli.main(
            [
                "verify",
                "--bundle",
                str(bundle),
                "--expected-sha",
                COMMIT_SHA,
                "--expected-manifest-sha256",
                manifest_sha256,
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "distribution bundle created" in output
    assert "distribution bundle verified" in output


@pytest.mark.parametrize(
    "git_payload",
    (
        {"sha": "d" * GIT_SHA_LENGTH, "branch": "main", "dirty": False},
        {"sha": COMMIT_SHA, "branch": "main", "dirty": True},
    ),
)
def test_create_cli_requires_exact_clean_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    git_payload: dict[str, object],
) -> None:
    """A wrong or dirty checkout cannot mint distribution evidence."""

    monkeypatch.setattr(
        cli.git_state,
        "git_state",
        partial(selected_git_state, payload=git_payload),
    )
    bundle = tmp_path / "bundle"

    result = cli.main(
        [
            "create",
            "--source",
            str(source_distributions(tmp_path)),
            "--bundle",
            str(bundle),
            "--expected-sha",
            COMMIT_SHA,
        ]
    )

    assert result == ERROR_EXIT
    assert not bundle.exists()
    assert "release artifact error" in capsys.readouterr().err


def test_verify_cli_rejects_tampered_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command boundary reports a bounded failure for substituted bytes."""

    monkeypatch.setattr(cli.git_state, "git_state", clean_git_state)
    source = source_distributions(tmp_path)
    bundle = tmp_path / "bundle"
    assert (
        cli.main(
            [
                "create",
                "--source",
                str(source),
                "--bundle",
                str(bundle),
                "--expected-sha",
                COMMIT_SHA,
            ]
        )
        == 0
    )
    manifest_sha256 = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    wheel = next((bundle / "packages").glob("*.whl"))
    wheel.write_bytes(b"other")

    result = cli.main(
        [
            "verify",
            "--bundle",
            str(bundle),
            "--expected-sha",
            COMMIT_SHA,
            "--expected-manifest-sha256",
            manifest_sha256,
        ]
    )

    assert result == ERROR_EXIT
    assert "mismatch" in capsys.readouterr().err
