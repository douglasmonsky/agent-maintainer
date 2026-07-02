"""Property tests for setup advisor recommendation invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from agent_maintainer.assess.models import RepoEvidence
from agent_maintainer.assess.setup_advisor import build_setup_report

TRACKS = {"core", "agent", "hardening", "inspect"}
PRESETS = {
    "ai-agent-heavy",
    "existing-app",
    "legacy-ratchet",
    "manual-review",
    "strict-new-repo",
}


def evidence_strategy() -> st.SearchStrategy[RepoEvidence]:
    """Build repository shapes for advisor recommendations."""
    counts = st.integers(min_value=0, max_value=500)
    return st.builds(
        RepoEvidence,
        target=st.just("/repo"),
        has_agent_config=st.booleans(),
        has_pyproject=st.booleans(),
        has_git=st.booleans(),
        has_tests=st.booleans(),
        has_src=st.booleans(),
        has_ci=st.booleans(),
        has_pre_commit=st.booleans(),
        has_agent_guidance=st.booleans(),
        has_codex_hooks=st.booleans(),
        has_claude_hooks=st.booleans(),
        has_tach=st.booleans(),
        has_import_linter=st.booleans(),
        has_lock_file=st.booleans(),
        has_dependency_file=st.booleans(),
        has_package_json=st.booleans(),
        has_container_or_iac=st.booleans(),
        python_files=counts,
        source_files=counts,
        test_files=counts,
        yaml_files=counts,
        toml_files=counts,
        json_files=counts,
    )


@given(evidence=evidence_strategy())
@settings(deadline=None, max_examples=100)
def test_setup_advisor_commands_match_recommendation(
    evidence: RepoEvidence,
) -> None:
    """Advisor commands stay aligned with recommended track and preset."""
    report = build_setup_report(evidence)

    assert report.track in TRACKS
    assert report.preset in PRESETS
    assert report.confidence in {"low", "medium", "high"}
    assert report.evidence == evidence
    assert len({gate.name for gate in report.optional_gates}) == len(
        report.optional_gates,
    )
    if report.track == "inspect":
        assert report.next_commands[1] == "agent-maintainer init --track core --dry-run"
        return
    dry_run, install, doctor, verify = report.next_commands
    expected_init = f"agent-maintainer init --track {report.track} --preset {report.preset}"
    assert dry_run == f"{expected_init} --dry-run"
    assert install == expected_init
    assert doctor == "agent-maintainer doctor"
    assert verify == "agent-maintainer verify --profile precommit"
