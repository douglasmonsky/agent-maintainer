"""Tests for generated Pyright project configuration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.runners import pyright as run_pyright
from tests.support.callbacks import constant_callback


def test_write_pyright_config_uses_maintainer_mode_and_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = MaintainerConfig(
        package_paths=("scripts", ".codex/hooks"),
        test_roots=("tests",),
        pyright_type_checking_mode="strict",
    )

    log_dir = tmp_path / ".verify-logs"
    path = run_pyright.write_pyright_config(log_dir, config)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["typeCheckingMode"] == "strict"
    assert payload["include"] == ["../scripts", "../.codex/hooks", "../tests"]
    assert payload["extraPaths"] == ["..", "../src"]
    assert "../.venv" in payload["exclude"]


def test_run_pyright_writes_json_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "pyrightconfig.generated.json"
    config_path.write_text("{}", encoding="utf-8")
    json_path = tmp_path / "pyright.json"

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--outputjson" in command
        assert "--pythonpath" in command
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"summary": {"filesAnalyzed": 3, "errorCount": 0}}\n',
            stderr="",
        )

    monkeypatch.setattr(run_pyright.shutil, "which", constant_callback("/usr/bin/pyright"))
    monkeypatch.setattr(run_pyright.subprocess, "run", fake_run)

    assert run_pyright.run_pyright(config_path, json_path) == 0

    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["errorCount"] == 0
    assert '"errorCount": 0' in capsys.readouterr().out


def test_run_pyright_fails_when_no_files_are_analyzed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "pyrightconfig.generated.json"
    config_path.write_text("{}", encoding="utf-8")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"summary": {"filesAnalyzed": 0, "errorCount": 0}}\n',
            stderr="",
        )

    monkeypatch.setattr(run_pyright.shutil, "which", constant_callback("/usr/bin/pyright"))
    monkeypatch.setattr(run_pyright.subprocess, "run", fake_run)

    assert run_pyright.run_pyright(config_path) == 1
    assert "analyzed 0 files" in capsys.readouterr().err


def test_python_interpreter_prefers_project_virtualenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    assert run_pyright.python_interpreter() == ".venv/bin/python"


def test_python_interpreter_falls_back_to_current_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert run_pyright.python_interpreter() == sys.executable


@pytest.mark.parametrize("output", ["", "{", '{"summary": []}'])
def test_analyzed_file_count_handles_missing_or_invalid_json(output: str) -> None:
    assert run_pyright.analyzed_file_count(output) is None


def test_analyzed_file_count_handles_missing_summary_count() -> None:
    assert run_pyright.analyzed_file_count('{"summary": {}}') is None


def test_main_uses_configured_diagnostic_artifact_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    diagnostic_dir = tmp_path / "custom-logs"
    config = MaintainerConfig(diagnostic_artifacts_dir=str(diagnostic_dir))
    seen_paths: dict[str, Path] = {}

    def fake_run_pyright(config_path: Path, json_path: Path | None) -> int:
        seen_paths["config"] = config_path
        assert json_path is not None
        seen_paths["json"] = json_path
        return 0

    monkeypatch.setattr(run_pyright, "load_config", lambda: config)
    monkeypatch.setattr(run_pyright, "run_pyright", fake_run_pyright)

    assert run_pyright.main() == 0

    assert seen_paths["config"] == diagnostic_dir / "pyrightconfig.generated.json"
    assert seen_paths["json"] == diagnostic_dir / "pyright.json"
    assert seen_paths["config"].exists()


def test_write_json_output_skips_blank_output(tmp_path: Path) -> None:
    path = tmp_path / "pyright.json"

    run_pyright.write_json_output(path, "\n")

    assert not path.exists()
