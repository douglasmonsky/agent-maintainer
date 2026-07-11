"""Tests for the Mutmut maintainer runner."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest

from agent_maintainer.runners import mutmut as run_mutmut
from agent_maintainer.runners import mutmut_stats
from tests.support.callbacks import constant_callback

MUTMUT_FAILURE_EXIT = 2


def test_main_passes_arguments_to_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI forwards Mutmut arguments to the runner."""

    seen_args: list[str] = []
    seen_ratchets: list[mutmut_stats.MutmutRatchet] = []

    def fake_run_mutmut(
        args: list[str],
        *,
        ratchet: mutmut_stats.MutmutRatchet,
    ) -> int:
        seen_args.extend(args)
        seen_ratchets.append(ratchet)
        return 0

    monkeypatch.setattr(run_mutmut, "run_mutmut", fake_run_mutmut)

    assert run_mutmut.main(["run", "--use-coverage"]) == 0
    assert seen_args == ["run", "--use-coverage"]
    assert seen_ratchets == [mutmut_stats.MutmutRatchet()]


def test_main_parses_result_ratchet_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runner CLI parses Agent Maintainer result-ratchet flags."""

    seen_args: list[str] = []
    seen_ratchets: list[mutmut_stats.MutmutRatchet] = []

    def fake_run_mutmut(
        args: list[str],
        *,
        ratchet: mutmut_stats.MutmutRatchet,
    ) -> int:
        seen_args.extend(args)
        seen_ratchets.append(ratchet)
        return 0

    monkeypatch.setattr(run_mutmut, "run_mutmut", fake_run_mutmut)

    assert (
        run_mutmut.main(
            [
                "--max-survivors",
                "84",
                "--max-suspicious",
                "0",
                "--max-timeouts",
                "0",
                "--min-score",
                "71",
                "run",
            ]
        )
        == 0
    )
    assert seen_args == ["run"]
    assert seen_ratchets == [
        mutmut_stats.MutmutRatchet(
            enabled=True,
            max_survivors=84,
            max_suspicious=0,
            max_timeouts=0,
            min_score=71,
        )
    ]


def test_successful_mutmut_run_removes_mutants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful runs clean generated mutation artifacts by default."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / "mutants").mkdir()
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["/usr/bin/mutmut", "run"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    assert run_mutmut.run_mutmut(["run"]) == 0
    assert not (tmp_path / "mutants").exists()


def test_mutmut_run_forwards_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mutmut stdout and stderr are forwarded to the verifier."""

    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="warn\n")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    assert run_mutmut.run_mutmut(["run"]) == 0
    captured = capsys.readouterr()
    assert "ok\n" in captured.out
    assert "warn\n" in captured.err


def test_failed_mutmut_run_skips_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed Mutmut command returns immediately and keeps artifacts."""
    cleanup_called = False

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, MUTMUT_FAILURE_EXIT, stdout="", stderr="")

    def fake_cleanup() -> None:
        nonlocal cleanup_called
        cleanup_called = True

    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")
    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)
    monkeypatch.setattr(run_mutmut, "cleanup_mutants", fake_cleanup)

    assert run_mutmut.run_mutmut(["run"]) == MUTMUT_FAILURE_EXIT
    assert cleanup_called is False


def test_mutmut_run_holds_lock_through_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runner serializes Mutmut command and generated-artifact cleanup."""
    events: list[str] = []

    @contextmanager
    def fake_lock() -> Generator[None, None, None]:
        events.append("lock")
        yield
        events.append("unlock")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        events.append("run")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def fake_cleanup() -> None:
        events.append("cleanup")

    monkeypatch.setattr(run_mutmut.mutmut_lock, "mutmut_run_lock", fake_lock)
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")
    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)
    monkeypatch.setattr(run_mutmut, "cleanup_mutants", fake_cleanup)

    assert run_mutmut.run_mutmut(["run"]) == 0

    assert events == ["lock", "run", "cleanup", "unlock"]


def test_mutmut_lock_allows_fcntl_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock helper degrades to no-op on platforms without fcntl."""

    monkeypatch.setattr(run_mutmut.mutmut_lock, "fcntl", None)
    monkeypatch.setenv(
        run_mutmut.mutmut_lock.DIAGNOSTIC_ARTIFACTS_DIR_ENV,
        str(tmp_path),
    )

    with run_mutmut.mutmut_lock.mutmut_run_lock():
        assert (tmp_path / "mutmut.lock").exists()


def test_mutmut_lock_defaults_to_verify_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock helper defaults to local verification logs."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(run_mutmut.mutmut_lock.DIAGNOSTIC_ARTIFACTS_DIR_ENV, raising=False)
    monkeypatch.setattr(run_mutmut.mutmut_lock, "fcntl", None)

    with run_mutmut.mutmut_lock.mutmut_run_lock():
        assert (tmp_path / ".verify-logs" / "mutmut.lock").exists()


def test_mutmut_result_ratchet_fails_and_keeps_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mutmut result-ratchet failure keeps mutants for inspection."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / "mutants").mkdir()
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["/usr/bin/mutmut", "export-cicd-stats"]:
            write_stats(tmp_path / "mutants" / "mutmut-cicd-stats.json", survived=1, total=2)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    result = run_mutmut.run_mutmut(
        ["run"],
        ratchet=mutmut_stats.MutmutRatchet(enabled=True, max_survivors=0),
    )

    assert result == 1
    assert (tmp_path / "mutants").exists()
    assert "mutmut survived mutants 1 above allowed 0" in capsys.readouterr().out


def test_mutmut_result_ratchet_passes_and_cleans_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passing Mutmut result ratchets still remove generated mutants."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / "mutants").mkdir()
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["/usr/bin/mutmut", "export-cicd-stats"]:
            write_stats(tmp_path / "mutants" / "mutmut-cicd-stats.json", survived=0, total=2)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    result = run_mutmut.run_mutmut(
        ["run"],
        ratchet=mutmut_stats.MutmutRatchet(enabled=True, max_survivors=0, min_score=100),
    )

    assert result == 0
    assert not (tmp_path / "mutants").exists()


def test_successful_mutmut_run_keeps_mutants_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AGENT_MAINTAINER_KEEP_MUTANTS preserves generated mutation artifacts."""

    monkeypatch.chdir(tmp_path)
    mutants = tmp_path / "mutants"
    mutants.mkdir()
    monkeypatch.setenv(run_mutmut.KEEP_MUTANTS_ENV, "true")
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    assert run_mutmut.run_mutmut(["run"]) == 0
    assert mutants.exists()


def test_mutmut_executable_falls_back_to_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The runner falls back to invoking mutmut by name."""

    monkeypatch.setattr(run_mutmut.shutil, "which", constant_callback(None))

    assert run_mutmut.mutmut_executable() == "mutmut"


def write_stats(path: Path, *, survived: int, total: int) -> None:
    """Write minimal Mutmut CI stats."""

    path.write_text(
        json.dumps(
            {
                "killed": total - survived,
                "survived": survived,
                "total": total,
                "no_tests": 0,
                "skipped": 0,
                "suspicious": 0,
                "timeout": 0,
                "check_was_interrupted_by_user": 0,
                "segfault": 0,
            }
        ),
        encoding="utf-8",
    )
