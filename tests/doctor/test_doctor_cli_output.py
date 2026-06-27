"""Tests doctor CLI output contracts."""

from __future__ import annotations

import json

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import models as maintainer_doctor_models


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
