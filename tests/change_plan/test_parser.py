"""Tests cohesive change plan parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.change_plan import parser
from agent_maintainer.change_plan.models import REQUIRED_SECTIONS

PLAN_FILE_LIMIT = 120


def test_parse_valid_plan_metadata_and_sections(tmp_path: Path) -> None:
    """Valid cohesive change plan parses metadata and required sections."""

    path = tmp_path / "plan.md"
    plan = parser.parse_plan_text(valid_plan_text(), path=path)

    assert plan.path == path
    assert plan.metadata.id == "package-migration"
    assert plan.metadata.allowed_paths == ("src/**", "tests/**")
    assert plan.metadata.max_changed_files == PLAN_FILE_LIMIT
    assert all(parser.normalized_heading(section) in plan.sections for section in REQUIRED_SECTIONS)


def test_parse_integration_branch_series_metadata(tmp_path: Path) -> None:
    """Integration branch series metadata parses when present."""

    metadata = (
        'integration_branch = "ratchet/package-migration"\n'
        'target_branch = "main"\n'
        'merge_strategy = "squash-after-series"\n'
        'expected_units = ["move config modules", "update tests"]\n'
    )
    plan = parser.parse_plan_text(
        valid_plan_text(extra_metadata=metadata).replace(
            'kind = "mechanical-migration"', 'kind = "integration-branch-series"'
        ),
        path=tmp_path / "plan.md",
    )

    assert plan.metadata.integration_branch == "ratchet/package-migration"
    assert plan.metadata.target_branch == "main"
    assert plan.metadata.merge_strategy == "squash-after-series"
    assert plan.metadata.expected_units == ("move config modules", "update tests")


def test_parse_rejects_missing_front_matter(tmp_path: Path) -> None:
    """Plan files must use TOML front matter delimiters."""

    with pytest.raises(parser.PlanParseError, match="missing opening"):
        parser.parse_plan_text("# Missing front matter", path=tmp_path / "bad.md")


def test_parse_rejects_missing_closing_front_matter(tmp_path: Path) -> None:
    """Plan files must close TOML front matter delimiters."""

    with pytest.raises(parser.PlanParseError, match="missing closing"):
        parser.parse_plan_text("+++\nid = 'missing-close'\n", path=tmp_path / "bad.md")


def test_parse_rejects_invalid_toml(tmp_path: Path) -> None:
    """Invalid TOML front matter reports parse errors."""

    with pytest.raises(parser.PlanParseError, match="invalid TOML"):
        parser.parse_plan_text("+++\n[\n+++\n", path=tmp_path / "bad.md")


def test_parse_rejects_invalid_metadata(tmp_path: Path) -> None:
    """Invalid metadata types fail during parsing."""

    text = valid_plan_text().replace("max_changed_files = 120", 'max_changed_files = "many"')

    with pytest.raises(parser.PlanParseError, match="invalid plan metadata"):
        parser.parse_plan_text(text, path=tmp_path / "bad.md")


def test_parse_rejects_invalid_string_list_metadata(tmp_path: Path) -> None:
    """Path arrays must contain only strings."""

    text = valid_plan_text().replace(
        'allowed_paths = ["src/**", "tests/**"]',
        'allowed_paths = ["src/**", 1]',
    )

    with pytest.raises(parser.PlanParseError, match="path lists"):
        parser.parse_plan_text(text, path=tmp_path / "bad.md")


def valid_plan_text(
    *, expires: str = "2099-01-01", omit_section: str = "", extra_metadata: str = ""
) -> str:
    """Return a valid cohesive change plan fixture."""

    sections = [
        f"## {section}\nThis section has a concrete explanation."
        for section in REQUIRED_SECTIONS
        if section != omit_section
    ]
    return (
        "+++\n"
        'id = "package-migration"\n'
        'kind = "mechanical-migration"\n'
        'status = "active"\n'
        'base_ref = "origin/main"\n'
        f"{extra_metadata}"
        f"expires = {expires}\n"
        'allowed_paths = ["src/**", "tests/**"]\n'
        'forbidden_paths = ["config/prod/**"]\n'
        "max_changed_files = 120\n"
        "max_changed_lines = 12000\n"
        "allow_source_without_test_change = false\n"
        "requires_tests = true\n"
        "requires_full_verify = true\n"
        'ratchet_targets = ["src/legacy/big_service.py"]\n'
        "+++\n"
        "# Cohesive Change Plan: Package migration\n\n" + "\n\n".join(sections) + "\n"
    )
