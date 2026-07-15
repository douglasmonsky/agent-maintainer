"""Tests the release-evidence filesystem and command boundary."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_maintainer import release_evidence as cli
from agent_run_artifacts import release_evidence

COMMIT_SHA = "c" * 40
ERROR_EXIT = 2


def clean_git_state(_root: Path) -> dict[str, object]:
    """Return the clean commit shared by CLI tests."""

    return {"sha": COMMIT_SHA, "branch": "main", "dirty": False}


def patch_clean_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make one CLI test operate from the expected clean commit."""

    monkeypatch.setattr(cli.git_state, "git_state", clean_git_state)


def profile_manifest(profile: str) -> dict[str, object]:
    """Return one recent clean profile manifest."""

    return {
        "version": 1,
        "profile": profile,
        "run_id": f"run-{profile}",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git": {"sha": COMMIT_SHA, "branch": "main", "dirty": False},
        "checks": [{"name": f"{profile}-check", "status": "passed"}],
    }


def write_profile_manifests(root: Path) -> list[Path]:
    """Write the complete required profile matrix."""

    paths: list[Path] = []
    for profile in release_evidence.REQUIRED_PROFILES:
        path = root / f"{profile}.json"
        path.write_text(
            json.dumps(profile_manifest(profile)),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


@pytest.mark.owner_contract
def test_aggregate_and_validate_cli_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI writes and revalidates a self-contained aggregate."""

    patch_clean_checkout(monkeypatch)
    manifests = write_profile_manifests(tmp_path)
    output = tmp_path / "release-evidence.json"
    aggregate_args = [
        "aggregate",
        "--expected-sha",
        COMMIT_SHA,
        "--output",
        str(output),
    ]
    for manifest in manifests:
        aggregate_args.extend(("--manifest", str(manifest)))

    assert cli.main(aggregate_args) == 0
    assert (
        cli.main(
            [
                "validate",
                "--expected-sha",
                COMMIT_SHA,
                "--manifest",
                str(output),
            ]
        )
        == 0
    )
    assert "release evidence aggregated" in capsys.readouterr().out


def test_aggregate_cli_does_not_write_partial_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid input returns a bounded error and leaves no aggregate."""

    patch_clean_checkout(monkeypatch)
    manifests = write_profile_manifests(tmp_path)[:-1]
    output = tmp_path / "release-evidence.json"
    args = [
        "aggregate",
        "--expected-sha",
        COMMIT_SHA,
        "--output",
        str(output),
    ]
    for manifest in manifests:
        args.extend(("--manifest", str(manifest)))

    assert cli.main(args) == ERROR_EXIT
    assert not output.exists()
    assert "missing required profiles: release" in capsys.readouterr().err


@pytest.mark.parametrize("exit_code", (0, 7))
def test_record_cli_writes_release_command_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
) -> None:
    """The release command's real terminal code is recorded and returned."""

    patch_clean_checkout(monkeypatch)

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["just", "release-check"]
        assert cwd == Path.cwd()
        assert check is False
        return subprocess.CompletedProcess(command, exit_code)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    output = tmp_path / "release.json"

    result = cli.main(
        [
            "record",
            "--output",
            str(output),
            "--",
            "just",
            "release-check",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == exit_code
    assert payload["profile"] == "release"
    checks = payload["checks"]
    assert isinstance(checks, list)
    assert checks[0]["status"] == ("passed" if exit_code == 0 else "failed")


def test_validate_cli_rejects_symlinked_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Evidence input cannot redirect the validator through a symlink."""

    patch_clean_checkout(monkeypatch)
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "evidence.json"
    link.symlink_to(target)

    assert (
        cli.main(
            [
                "validate",
                "--expected-sha",
                COMMIT_SHA,
                "--manifest",
                str(link),
            ]
        )
        == ERROR_EXIT
    )
    assert "must not be a symlink" in capsys.readouterr().err


def test_validate_cli_rejects_oversized_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Evidence reads stop at a fixed byte ceiling."""

    patch_clean_checkout(monkeypatch)
    manifest = tmp_path / "evidence.json"
    manifest.write_bytes(b"x" * (cli.MAX_MANIFEST_BYTES + 1))

    assert (
        cli.main(
            [
                "validate",
                "--expected-sha",
                COMMIT_SHA,
                "--manifest",
                str(manifest),
            ]
        )
        == ERROR_EXIT
    )
    assert "exceeds byte limit" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("git", "message"),
    (
        (
            {"sha": "d" * 40, "branch": "main", "dirty": False},
            "current checkout does not match expected commit",
        ),
        (
            {"sha": COMMIT_SHA, "branch": "main", "dirty": True},
            "current checkout is dirty",
        ),
    ),
)
def test_validate_cli_rejects_wrong_or_dirty_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    git: dict[str, object],
    message: str,
) -> None:
    """Artifact validity cannot substitute for the consumer checkout identity."""

    def selected_git_state(_root: Path) -> dict[str, object]:
        return git

    monkeypatch.setattr(cli.git_state, "git_state", selected_git_state)
    manifest = tmp_path / "evidence.json"
    manifest.write_text("{}", encoding="utf-8")

    assert (
        cli.main(
            [
                "validate",
                "--expected-sha",
                COMMIT_SHA,
                "--manifest",
                str(manifest),
            ]
        )
        == ERROR_EXIT
    )
    assert message in capsys.readouterr().err
