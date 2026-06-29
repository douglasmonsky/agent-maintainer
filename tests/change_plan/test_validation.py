"""Tests cohesive change plan validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from agent_maintainer.change_plan import parser, templates, validation
from tests.change_plan.test_parser import valid_plan_text


def test_valid_plan_passes_validation(tmp_path: Path) -> None:
    """Complete active plan passes validation."""

    plan = parser.parse_plan_text(valid_plan_text(), path=tmp_path / "plan.md")

    assert validation.validate_plan(plan, today=date(2026, 6, 29)) == ()


def test_expired_plan_fails_validation(tmp_path: Path) -> None:
    """Expired plans cannot authorize large changes."""

    plan = parser.parse_plan_text(valid_plan_text(expires="2026-06-01"), path=tmp_path / "plan.md")

    issues = validation.validate_plan(plan, today=date(2026, 6, 29))

    assert any("expired" in issue.message for issue in issues)


def test_missing_required_section_fails_validation(tmp_path: Path) -> None:
    """Plans must explain every required review field."""

    plan = parser.parse_plan_text(
        valid_plan_text(omit_section="Rollback plan"), path=tmp_path / "plan.md"
    )

    issues = validation.validate_plan(plan, today=date(2026, 6, 29))

    assert any("Rollback plan" in issue.message for issue in issues)


def test_template_contains_required_sections() -> None:
    """Generated starter templates include all required sections."""

    rendered = templates.render_plan_template("package-migration", today=date(2026, 6, 29))

    assert 'id = "package-migration"' in rendered
    assert "expires = 2026-07-13" in rendered
    assert all(f"## {section}" in rendered for section in validation.REQUIRED_SECTIONS)


def test_requires_full_verify_must_be_true(tmp_path: Path) -> None:
    """Large-change plans must keep full verification required."""

    text = valid_plan_text().replace("requires_full_verify = true", "requires_full_verify = false")
    plan = parser.parse_plan_text(text, path=tmp_path / "plan.md")

    issues = validation.validate_plan(plan, today=date(2026, 6, 29))

    assert any("requires_full_verify" in issue.message for issue in issues)


def test_metadata_validation_reports_all_policy_failures(tmp_path: Path) -> None:
    """Metadata validation reports strict policy failures."""

    plan = parser.parse_plan_text(valid_plan_text(), path=tmp_path / "plan.md")
    metadata = replace(
        plan.metadata,
        status="draft",
        allowed_paths=(),
        max_changed_files=0,
        max_changed_lines=0,
        ratchet_targets=("README.md",),
    )
    plan = replace(plan, metadata=metadata)

    issues = validation.validate_plan(plan, today=date(2026, 6, 29))
    messages = {issue.message for issue in issues}

    assert "status must be 'active'" in messages
    assert "allowed_paths must contain at least one pattern" in messages
    assert "max_changed_files must be positive" in messages
    assert "max_changed_lines must be positive" in messages
    assert "ratchet_targets must point to Python files" in messages
