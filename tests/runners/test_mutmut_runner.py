"""Tests Mutmut maintainer runner cleanup behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.runners import mutmut as run_mutmut


def test_main_passes_arguments_to_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_args: list[str] = []

    def fake_run_mutmut(args: list[str]) -> int:
        seen_args.extend(args)
        return 0

    monkeypatch.setattr(run_mutmut, "run_mutmut", fake_run_mutmut)

    assert run_mutmut.main(["run", "--use-coverage"]) == 0
    assert seen_args == ["run", "--use-coverage"]


def test_successful_mutmut_run_removes_mutants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="warn\n")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    assert run_mutmut.run_mutmut(["run"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "ok\n"
    assert captured.err == "warn\n"


def test_failed_mutmut_run_preserves_mutants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    mutants = tmp_path / "mutants"
    mutants.mkdir()
    monkeypatch.setattr(run_mutmut, "mutmut_executable", lambda: "/usr/bin/mutmut")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr(run_mutmut.subprocess, "run", fake_run)

    assert run_mutmut.run_mutmut(["run"]) == 1
    assert mutants.exists()


def test_keep_mutants_env_preserves_successful_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    monkeypatch.setattr(run_mutmut.shutil, "which", lambda name: None)

    assert run_mutmut.mutmut_executable() == "mutmut"
