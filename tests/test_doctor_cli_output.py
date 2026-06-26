"""Tests doctor CLI output contracts."""

from __future__ import annotations

import json

import pytest

from ai_guardrails.core.config import GuardrailConfig
from ai_guardrails.doctor import cli as guardrail_doctor
from ai_guardrails.doctor.support import models as guardrail_doctor_models


def test_main_emits_json_with_state_and_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(guardrail_doctor.guardrail_config, "load_config", GuardrailConfig)
    monkeypatch.setattr(
        guardrail_doctor,
        "run_doctor",
        lambda repo_root, config: [
            guardrail_doctor.DoctorResult(
                "python-version",
                guardrail_doctor.OK,
                "ok",
                hint="already fine",
            )
        ],
    )

    assert guardrail_doctor.main(["--json"]) == 0

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
    monkeypatch.setattr(guardrail_doctor.guardrail_config, "load_config", GuardrailConfig)
    monkeypatch.setattr(
        guardrail_doctor,
        "run_doctor",
        lambda repo_root, config: [
            guardrail_doctor.DoctorResult(
                "virtualenv",
                guardrail_doctor.WARNING,
                "missing",
                state=guardrail_doctor_models.MISSING,
                hint="bootstrap",
            )
        ],
    )

    assert guardrail_doctor.main([]) == 0

    assert "WARN virtualenv [missing]: missing Hint: bootstrap" in capsys.readouterr().out
