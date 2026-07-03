"""Tests cohesive change plan validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from agent_maintainer.change_plan import parser, templates, validation
from tests.change_plan.test_parser import valid_plan_text


# docsync:evidence.start evidence.change_plans.validation_tests
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


def test_template_contains_integration_branch_series_fields() -> None:
    """Generated integration branch templates include branch metadata."""

    rendered = templates.render_plan_template(
        "package-migration",
        kind="integration-branch-series",
        integration_branch=templates.IntegrationBranchTemplate(
            branch="ratchet/package-migration",
            expected_units=("move config modules", "update tests"),
        ),
        today=date(2026, 6, 29),
    )

    assert 'kind = "integration-branch-series"' in rendered
    assert 'integration_branch = "ratchet/package-migration"' in rendered
    assert 'target_branch = "main"' in rendered
    assert 'merge_strategy = "squash-after-series"' in rendered
    assert '"move config modules"' in rendered
    assert '"update tests"' in rendered


# docsync:evidence.end evidence.change_plans.validation_tests


def test_integration_branch_series_metadata_passes_validation(tmp_path: Path) -> None:
    """Complete integration branch metadata passes validation."""

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

    assert validation.validate_plan(plan, today=date(2026, 6, 29)) == ()


def test_integration_branch_series_requires_branch_fields(tmp_path: Path) -> None:
    """Integration branch plans must describe the branch series."""

    plan = parser.parse_plan_text(
        valid_plan_text().replace(
            'kind = "mechanical-migration"', 'kind = "integration-branch-series"'
        ),
        path=tmp_path / "plan.md",
    )

    issues = validation.validate_plan(plan, today=date(2026, 6, 29))
    messages = {issue.message for issue in issues}

    assert "integration_branch must be set for integration-branch-series" in messages
    assert "target_branch must be set for integration-branch-series" in messages
    assert "merge_strategy must be set for integration-branch-series" in messages
    assert "expected_units must list planned integration units" in messages


def test_integration_branch_series_rejects_whitespace_branch_names(
    tmp_path: Path,
) -> None:
    """Branch-series metadata must not contain whitespace."""

    metadata = (
        'integration_branch = "ratchet/package migration"\n'
        'target_branch = "main"\n'
        'merge_strategy = "squash-after-series"\n'
        'expected_units = ["move config modules"]\n'
    )
    plan = parser.parse_plan_text(
        valid_plan_text(extra_metadata=metadata).replace(
            'kind = "mechanical-migration"', 'kind = "integration-branch-series"'
        ),
        path=tmp_path / "plan.md",
    )

    issues = validation.validate_plan(plan, today=date(2026, 6, 29))

    assert any(
        "integration_branch must not contain whitespace" in issue.message for issue in issues
    )


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
