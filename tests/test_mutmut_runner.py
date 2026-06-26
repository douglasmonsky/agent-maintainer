"""Tests Mutmut guardrail runner cleanup behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import run_mutmut


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
