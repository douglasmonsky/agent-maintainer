"""Tests doctor CLI output contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.doctor.support import output as maintainer_doctor_output


class DoctorRunRecorder:
    """Callable test helper that records doctor main inputs."""

    def __init__(self, result: maintainer_doctor.DoctorResult) -> None:
        self.result = result
        self.repo_root: Path | None = None
        self.config: MaintainerConfig | None = None

    def __call__(
        self,
        repo_root: Path,
        loaded_config: MaintainerConfig,
    ) -> list[maintainer_doctor.DoctorResult]:
        """Record doctor inputs and return the configured result."""

        self.repo_root = repo_root
        self.config = loaded_config
        return [self.result]


def test_main_emits_json_with_state_and_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(maintainer_doctor.maintainer_config, "load_config", MaintainerConfig)
    monkeypatch.setattr(
        maintainer_doctor,
        "run_doctor",
        lambda repo_root, config: [
            maintainer_doctor.DoctorResult(
                "python-version",
                maintainer_doctor.OK,
                "ok",
                hint="already fine",
            )
        ],
    )

    assert maintainer_doctor.main(["--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == [
        {
            "name": "python-version",
            "status": "PASS",
            "message": "ok",
            "state": "active",
            "hint": "already fine",
        }
    ]


def test_main_emits_json_with_format_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(maintainer_doctor.maintainer_config, "load_config", MaintainerConfig)
    monkeypatch.setattr(
        maintainer_doctor,
        "run_doctor",
        lambda repo_root, config: [
            maintainer_doctor.DoctorResult("repo-root", maintainer_doctor.OK, "ok")
        ],
    )

    assert maintainer_doctor.main(["--format", "json"]) == 0

    assert json.loads(capsys.readouterr().out)[0]["name"] == "repo-root"


def test_parse_args_defaults_and_flags() -> None:
    defaults = maintainer_doctor.parse_args([])
    explicit = maintainer_doctor.parse_args(["--strict", "--json", "--format", "json"])
    assert defaults.strict is False
    assert defaults.json is False
    assert defaults.format == "text"
    assert explicit.strict is True
    assert explicit.json is True
    assert explicit.format == "json"


def test_parse_args_help_lists_json_and_strict(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        maintainer_doctor.parse_args(["--help"])
    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "--strict" in output
    assert "--json" in output
    assert "--format" in output
    assert "--root" in output


def test_main_loads_config_from_explicit_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    outside = tmp_path / "outside"
    repo_root = tmp_path / "repo"
    outside.mkdir()
    repo_root.mkdir()
    monkeypatch.chdir(outside)
    recorder = DoctorRunRecorder(
        maintainer_doctor.DoctorResult("repo-root", maintainer_doctor.OK, "ok")
    )
    loaded_from: list[Path] = []

    def fake_load_config() -> MaintainerConfig:
        loaded_from.append(Path.cwd())
        return MaintainerConfig()

    monkeypatch.setattr(maintainer_doctor.maintainer_config, "load_config", fake_load_config)
    monkeypatch.setattr(maintainer_doctor, "run_doctor", recorder)

    assert maintainer_doctor.main(["--root", str(repo_root)]) == 0

    assert loaded_from == [repo_root]
    assert Path.cwd() == outside
    assert recorder.repo_root == repo_root
    assert "PASS repo-root" in capsys.readouterr().out


def test_main_emits_text_with_state_and_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(maintainer_doctor.maintainer_config, "load_config", MaintainerConfig)
    monkeypatch.setattr(
        maintainer_doctor,
        "run_doctor",
        lambda repo_root, config: [
            maintainer_doctor.DoctorResult(
                "virtualenv",
                maintainer_doctor.WARNING,
                "missing",
                state=maintainer_doctor_models.MISSING,
                hint="bootstrap",
            )
        ],
    )

    assert maintainer_doctor.main([]) == 0

    assert "WARN virtualenv [missing]: missing Hint: bootstrap" in capsys.readouterr().out


def test_main_strict_returns_nonzero_for_warning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(maintainer_doctor.maintainer_config, "load_config", MaintainerConfig)
    monkeypatch.setattr(
        maintainer_doctor,
        "run_doctor",
        lambda repo_root, config: [
            maintainer_doctor.DoctorResult(
                "git-state",
                maintainer_doctor.WARNING,
                "ahead",
            )
        ],
    )

    assert maintainer_doctor.main(["--strict"]) == 1
    assert "WARN git-state [active]: ahead" in capsys.readouterr().out


def test_main_uses_cwd_and_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = MaintainerConfig(mode="fresh-strict")
    recorder = DoctorRunRecorder(
        maintainer_doctor.DoctorResult("python-version", maintainer_doctor.OK, "ok")
    )

    monkeypatch.setattr(
        maintainer_doctor.Path,
        "cwd",
        classmethod(lambda _path_type: tmp_path),
    )
    monkeypatch.setattr(maintainer_doctor.maintainer_config, "load_config", lambda: config)
    monkeypatch.setattr(maintainer_doctor, "run_doctor", recorder)

    assert maintainer_doctor.main([]) == 0
    assert recorder.repo_root == tmp_path
    assert recorder.config == config


def test_format_text_row_omits_empty_hint() -> None:
    result = maintainer_doctor.DoctorResult(
        "repo-root",
        maintainer_doctor.OK,
        "/repo",
    )

    assert maintainer_doctor_output.format_text_row(result) == "PASS repo-root [active]: /repo"


def test_status_code_strict_warning() -> None:
    warning = maintainer_doctor.DoctorResult(
        "git-state",
        maintainer_doctor.WARNING,
        "ahead 1",
    )
    failure = maintainer_doctor.DoctorResult(
        "layout",
        maintainer_doctor.ERROR,
        "missing source",
    )

    assert maintainer_doctor_output.status_code([warning], strict=False) == 0
    assert maintainer_doctor_output.status_code([warning], strict=True) == 1
    assert maintainer_doctor_output.status_code([failure], strict=False) == 1


def test_jsonable_results_keep_hint() -> None:
    result = maintainer_doctor.DoctorResult(
        "virtualenv",
        maintainer_doctor.WARNING,
        "missing",
        state=maintainer_doctor_models.MISSING,
        hint="bootstrap",
    )

    assert maintainer_doctor_output.results_to_jsonable([result]) == [
        {
            "name": "virtualenv",
            "status": "WARN",
            "message": "missing",
            "state": "missing",
            "hint": "bootstrap",
        }
    ]
