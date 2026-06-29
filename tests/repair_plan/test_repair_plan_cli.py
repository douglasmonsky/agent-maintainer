"""Tests non-mutating repair plan CLI."""

from __future__ import annotations

import json

import pytest

from agent_maintainer import cli as maintainer_cli
from agent_maintainer.repair_plan import cli as repair_plan_cli

DEFAULT_OUTPUT_BUDGET = 12_000
TIGHT_OUTPUT_BUDGET = 180
PRINT_NEWLINE_ALLOWANCE = 1


def test_repair_plan_default_markdown_has_required_sections(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Default repair plan emits bounded Markdown sections."""
    assert repair_plan_cli.main([]) == 0

    output = capsys.readouterr().out

    assert "# Repair Plan" in output
    for heading in (
        "## objective",
        "## current target",
        "## recommended sequence",
        "## context commands",
        "## test commands",
        "## verification commands",
        "## stop conditions",
    ):
        assert heading in output
    assert "python -m agent_maintainer verify --profile precommit" in output
    assert len(output) < DEFAULT_OUTPUT_BUDGET


def test_repair_plan_json_is_parseable(capsys: pytest.CaptureFixture[str]) -> None:
    """JSON repair plan exposes stable machine-readable fields."""
    assert repair_plan_cli.main(["--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload["mode"] == "default"
    assert payload["non_mutating"] is True
    assert payload["objective"]
    assert payload["context_commands"]
    assert payload["verification_commands"]


def test_repair_plan_ratchet_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Ratchet mode starts with ratchet target discovery."""
    assert repair_plan_cli.main(["--ratchet"]) == 0

    output = capsys.readouterr().out

    assert "Repair one ratchet target" in output
    assert "python -m agent_maintainer ratchet next --limit 5" in output
    assert "python -m agent_maintainer ratchet status" in output


def test_repair_plan_check_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Check mode points to the selected verifier log."""
    assert repair_plan_cli.main(["--check", "pyright"]) == 0

    output = capsys.readouterr().out

    assert "Verifier check: pyright" in output
    assert "python -m agent_maintainer context log pyright --tail 120" in output


def test_repair_plan_target_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Target mode points to bounded file and diff expansion."""
    assert repair_plan_cli.main(["--target", "src/legacy/big_service.py"]) == 0

    output = capsys.readouterr().out

    assert "Path: src/legacy/big_service.py" in output
    assert "context file src/legacy/big_service.py --outline" in output
    assert "context diff --path src/legacy/big_service.py --hunks 5" in output


def test_top_level_routes_repair_plan(capsys: pytest.CaptureFixture[str]) -> None:
    """Top-level CLI routes repair-plan command."""
    assert maintainer_cli.main(["repair-plan", "--check", "ruff"]) == 0

    output = capsys.readouterr().out

    assert "Verifier check: ruff" in output


def test_repair_plan_markdown_respects_budget(capsys: pytest.CaptureFixture[str]) -> None:
    """Repair plan output obeys explicit character budget."""
    assert repair_plan_cli.main(["--budget", str(TIGHT_OUTPUT_BUDGET)]) == 0

    output = capsys.readouterr().out

    assert len(output) <= TIGHT_OUTPUT_BUDGET + PRINT_NEWLINE_ALLOWANCE
