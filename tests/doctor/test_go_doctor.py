"""Tests Go provider doctor hints."""

from __future__ import annotations

import sys
from dataclasses import replace

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor.support import go as doctor_go
from agent_maintainer.doctor.support import providers as doctor_providers
from agent_maintainer.doctor.support.models import ACTIVE, MISSING, OK, UNSAFE_CONFIG, WARNING


def test_go_doctor_silent_when_disabled() -> None:
    """Disabled Go provider does not add command-setup noise."""
    assert doctor_go.check_go_provider(MaintainerConfig()) == ()


def test_go_doctor_warns_without_commands() -> None:
    """Enabled Go provider without commands gets concrete setup hint."""
    config = replace(MaintainerConfig(), enable_go=True)

    result = doctor_go.check_go_provider(config)[0]

    assert result.status == WARNING
    assert result.state == UNSAFE_CONFIG
    assert "no commands" in result.message
    assert "go_format_command" in result.hint


def test_go_doctor_warns_missing_executable() -> None:
    """Configured Go command executables must resolve."""
    config = replace(
        MaintainerConfig(),
        enable_go=True,
        go_test_command=("definitely-missing-agent-maintainer-go", "test", "./..."),
    )

    result = doctor_go.check_go_provider(config)[0]

    assert result.status == WARNING
    assert result.state == MISSING
    assert "go-test" in result.message
    assert "definitely-missing-agent-maintainer-go" in result.message


def test_go_doctor_passes_existing_executable() -> None:
    """Configured Go commands produce an active provider row."""
    config = replace(
        MaintainerConfig(),
        enable_go=True,
        go_test_command=(sys.executable, "--version"),
    )

    result = doctor_go.check_go_provider(config)[0]

    assert result.status == OK
    assert result.state == ACTIVE
    assert "go-test" in result.message


def test_provider_status_reports_maturity() -> None:
    """Doctor exposes provider maturity without warning on disabled experiments."""
    config = replace(MaintainerConfig(), enable_go=True)

    result = doctor_providers.check_provider_status(config)

    assert result.status == OK
    assert result.state == ACTIVE
    assert "Python core active" in result.message
    assert "TypeScript/JavaScript experimental disabled" in result.message
    assert "Go experimental active" in result.message
