"""Tests for Archguard architecture decision-note policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from archguard import decision_notes


def set_changed_paths(
    monkeypatch: pytest.MonkeyPatch,
    paths: tuple[str, ...],
) -> None:
    """Patch Archguard diff discovery to return known paths."""

    def fake_changed_paths(
        repo_root: Path,
        *,
        base_ref: str,
        staged: bool,
    ) -> tuple[str, ...]:
        assert repo_root
        assert base_ref
        assert isinstance(staged, bool)
        return paths

    monkeypatch.setattr(decision_notes, "changed_paths", fake_changed_paths)


def test_decision_check_passes_when_no_policy_files_changed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow ordinary source changes without architecture decision notes."""
    set_changed_paths(monkeypatch, ("src/app.py", "tests/test_app.py"))

    assert (
        decision_notes.decision_check_failures(
            tmp_path,
            base_ref="HEAD",
            staged=False,
        )
        == []
    )


def test_decision_check_reports_git_diff_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Surface git diff discovery errors as decision-check failures."""

    def fail_changed_paths(*args: object, **kwargs: object) -> tuple[str, ...]:
        raise RuntimeError("bad git diff")

    monkeypatch.setattr(decision_notes, "changed_paths", fail_changed_paths)

    assert decision_notes.decision_check_failures(
        tmp_path,
        base_ref="HEAD",
        staged=False,
    ) == ["bad git diff"]


def test_decision_check_fails_when_tach_toml_changed_without_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require a decision note when root Tach policy changes."""
    set_changed_paths(monkeypatch, ("tach.toml",))

    failures = decision_notes.decision_check_failures(
        tmp_path,
        base_ref="HEAD",
        staged=False,
    )

    assert failures == [
        "architecture policy changed without decision note: tach.toml",
        "Add or update a decision note under docs/architecture/decisions/.",
    ]


def test_decision_check_passes_when_tach_toml_and_decision_note_changed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow Tach policy changes with matching architecture decision notes."""
    set_changed_paths(
        monkeypatch,
        (
            "tach.toml",
            "docs/architecture/decisions/2026-06-27-boundary.md",
        ),
    )

    assert (
        decision_notes.decision_check_failures(
            tmp_path,
            base_ref="HEAD",
            staged=False,
        )
        == []
    )


def test_decision_check_watches_nested_tach_domain_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Treat nested Tach domain files as architecture policy."""
    set_changed_paths(monkeypatch, ("services/billing/tach.domain.toml",))

    failures = decision_notes.decision_check_failures(
        tmp_path,
        base_ref="HEAD",
        staged=True,
    )

    assert failures[0] == (
        "architecture policy changed without decision note: services/billing/tach.domain.toml"
    )


def test_new_decision_note_creates_expected_template(tmp_path: Path) -> None:
    """Create a dated architecture decision note from a slug."""
    path = decision_notes.new_decision_note(
        tmp_path,
        "Allow Billing Users API",
        decision_root="docs/architecture/decisions",
    )

    assert path.parent == tmp_path / "docs/architecture/decisions"
    assert path.name.endswith("-allow-billing-users-api.md")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Architecture Decision: Allow Billing Users Api")
    assert "## Why is this not just architecture drift?" in text


def test_new_decision_note_keeps_existing_note(tmp_path: Path) -> None:
    """Do not overwrite an existing dated decision note."""
    path = decision_notes.new_decision_note(
        tmp_path,
        "Existing",
        decision_root="docs/architecture/decisions",
    )
    path.write_text("custom\n", encoding="utf-8")

    assert (
        decision_notes.new_decision_note(
            tmp_path,
            "Existing",
            decision_root="docs/architecture/decisions",
        )
        == path
    )
    assert path.read_text(encoding="utf-8") == "custom\n"


def test_slug_normalization_handles_spaces_and_symbols() -> None:
    """Normalize noisy decision-note titles into stable slugs."""
    assert decision_notes.normalize_slug(" Allow billing/users API! ") == "allow-billing-users-api"
    assert decision_notes.normalize_slug("!!!") == "architecture-decision"
