"""Tests cohesive-change override validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.checks import change_budget, cohesive_override
from agent_maintainer.core.config import MaintainerConfig


def enabled_config() -> MaintainerConfig:
    """Return config with a narrow cohesive override allowlist."""

    return MaintainerConfig(
        cohesive_change_override_enabled=True,
        cohesive_change_override_paths=("src/agent_maintainer/**",),
        cohesive_change_override_max_lines=20,
        cohesive_change_override_max_files=3,
    )


def test_file_change_shape_accepted() -> None:
    """Override policy accepts change-budget file-change records."""
    failures = cohesive_override.eligibility_failures(
        enabled_config(),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 2, 3)],
    )

    assert failures == ()


def valid_body() -> str:
    """Return valid PR body override section."""

    return """\
## Summary

Mechanical package movement.

## Cohesive-Change Override

- Override requested: yes
- Why this is one cohesive unit: package paths must move together.
- Why smaller PRs would make the repository less coherent: split imports would
  create temporary dead code and broken boundaries.
- Tests/verification proving behavior is unchanged: full verifier and focused
  package migration tests pass.
- Behavior change: none, behavior is unchanged.
"""


def set_github_pr_body(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str) -> None:
    """Set GitHub pull request event environment for override parsing."""

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"body": body}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.delenv("AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED", raising=False)


def test_valid_github_override_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Valid PR explanation and eligible changes allow hard-budget override."""

    set_github_pr_body(monkeypatch, tmp_path, valid_body())
    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 10, 2)],
    )

    assert decision.requested
    assert decision.allowed
    assert decision.failures == ()


def test_missing_required_pr_explanation_blocks_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A casual request without required fields cannot bypass budgets."""

    set_github_pr_body(
        monkeypatch,
        tmp_path,
        "## Cohesive-Change Override\n\n- Override requested: yes\n",
    )
    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 4, 0)],
    )

    assert decision.requested
    assert not decision.allowed
    assert any("missing required field" in failure for failure in decision.failures)


def test_overbroad_path_scope_blocks_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Every changed source file must match the configured allowlist."""

    set_github_pr_body(monkeypatch, tmp_path, valid_body())
    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [change_budget.FileChange("src/other_package/core.py", 4, 0)],
    )

    assert decision.requested
    assert not decision.allowed
    assert decision.failures == (
        "Cohesive-change override includes paths outside the allowlist: src/other_package/core.py.",
    )


def test_excessive_size_blocks_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Configured max override size remains a hard limit."""

    set_github_pr_body(monkeypatch, tmp_path, valid_body())
    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 21, 0)],
    )

    assert decision.requested
    assert not decision.allowed
    assert decision.failures == (
        "Cohesive-change override exceeds maximum size: 21 changed lines (limit: 20).",
    )


def test_no_override_request_preserves_normal_budget_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No PR section or local env means no override is requested."""

    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.delenv("AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED", raising=False)

    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 10, 0)],
    )

    assert not decision.requested
    assert not decision.allowed


def test_local_override_request_warns_ci_must_verify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local override can proceed only with explicit env and CI warning."""

    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.setenv("AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED", "1")
    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 10, 0)],
    )

    assert decision.requested
    assert decision.allowed
    assert "GitHub CI must verify" in decision.warnings[0]


def test_change_budget_main_accepts_eligible_local_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Change-budget command downgrades eligible override failures to warnings."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.setattr(
        change_budget,
        "run_git_numstat",
        lambda base_ref, staged=False: [
            change_budget.FileChange("src/agent_maintainer/core/config.py", 10, 0),
        ],
    )
    monkeypatch.setattr(
        change_budget,
        "load_config",
        lambda: enabled_config(),
    )
    monkeypatch.setenv("AGENT_MAINTAINER_COHESIVE_CHANGE_OVERRIDE_REQUESTED", "true")

    result = change_budget.main(["--block-lines", "3"])

    assert result == 0
    assert "Cohesive-change override requested locally" in capsys.readouterr().out


def test_github_pr_body_ignores_missing_event_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub PR parsing is opt-in to a real event payload path."""

    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)

    assert cohesive_override.github_pr_body() is None


def test_github_pr_body_ignores_missing_event_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing GitHub event files behave like no PR metadata."""

    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(tmp_path / "missing-event.json"))

    assert cohesive_override.github_pr_body() is None


def test_github_pr_body_ignores_malformed_pull_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Malformed GitHub events are ignored instead of guessed."""

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": []}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    assert cohesive_override.github_pr_body() is None


def test_github_pr_body_normalizes_non_string_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Non-string PR bodies become empty strings for parser safety."""

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"body": None}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    assert cohesive_override.github_pr_body() == ""


def test_parse_pr_body_without_override_section_is_not_requested() -> None:
    """Normal PR bodies do not request override handling."""

    request = cohesive_override.parse_pr_body("## Summary\n\nRegular change.")

    assert not request.requested


def test_behavior_change_field_must_state_unchanged() -> None:
    """Override metadata must say behavior remains unchanged."""

    body = valid_body().replace(
        "- Behavior change: none, behavior is unchanged.",
        "- Behavior change: adds new runtime behavior.",
    )

    request = cohesive_override.parse_pr_body(body)

    assert request.requested
    assert request.failures == ("Cohesive-change override must state behavior is unchanged.",)


def test_too_many_files_blocks_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Configured max file count remains hard limit."""

    set_github_pr_body(monkeypatch, tmp_path, valid_body())

    decision = cohesive_override.evaluate_override(
        enabled_config(),
        [
            change_budget.FileChange("src/agent_maintainer/a.py", 1, 0),
            change_budget.FileChange("src/agent_maintainer/b.py", 1, 0),
            change_budget.FileChange("src/agent_maintainer/c.py", 1, 0),
            change_budget.FileChange("src/agent_maintainer/d.py", 1, 0),
        ],
    )

    assert decision.requested
    assert not decision.allowed
    assert decision.failures == (
        "Cohesive-change override touches too many files: 4 files (limit: 3).",
    )


def test_disabled_or_unscoped_config_blocks_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Overrides require explicit repository enablement and path scope."""

    set_github_pr_body(monkeypatch, tmp_path, valid_body())

    decision = cohesive_override.evaluate_override(
        MaintainerConfig(cohesive_change_override_enabled=False),
        [change_budget.FileChange("src/agent_maintainer/core/config.py", 1, 0)],
    )

    assert decision.requested
    assert not decision.allowed
    assert decision.failures == (
        "Cohesive-change overrides are disabled for this repository.",
        "Cohesive-change override has no configured path allowlist.",
        "Cohesive-change override includes paths outside the allowlist: "
        "src/agent_maintainer/core/config.py.",
    )
