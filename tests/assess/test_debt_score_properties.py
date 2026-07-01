"""Property tests for advisory Technical Debt Score invariants."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from agent_maintainer.assess import debt_category_constants as constants
from agent_maintainer.assess.debt_categories import risk_label
from agent_maintainer.assess.debt_score import build_debt_report
from agent_maintainer.assess.models import RepoEvidence
from agent_maintainer.config.schema import MaintainerConfig

RISK_LABELS = {"low", "moderate", "high", "critical"}
LOW_RISK_MAX = constants.LOW_RISK_MAX
MODERATE_RISK_MAX = constants.MODERATE_RISK_MAX
HIGH_RISK_MAX = constants.HIGH_RISK_MAX
MAX_SCORE = constants.MAX_SCORE


def evidence_strategy() -> st.SearchStrategy[RepoEvidence]:
    """Build realistic repository evidence combinations."""
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
        has_go_mod=st.booleans(),
        has_container_or_iac=st.booleans(),
        python_files=counts,
        source_files=counts,
        test_files=counts,
        yaml_files=counts,
        toml_files=counts,
        json_files=counts,
    )


def config_strategy() -> st.SearchStrategy[MaintainerConfig]:
    """Build config combinations that should not break scoring."""
    return st.builds(
        MaintainerConfig,
        mode=st.sampled_from(("custom", "fresh-strict", "legacy-ratchet")),
        require_tests=st.booleans(),
        coverage_fail_under=st.integers(min_value=0, max_value=100),
        change_block_lines=st.integers(min_value=0, max_value=2_000),
        change_block_files=st.integers(min_value=0, max_value=100),
        file_length_max_physical=st.integers(min_value=1, max_value=2_000),
        file_length_max_source=st.integers(min_value=1, max_value=2_000),
        ruff_max_complexity=st.integers(min_value=1, max_value=30),
        pyright_type_checking_mode=st.sampled_from(("basic", "standard", "strict")),
        ratchet_enabled=st.booleans(),
        enable_wemake=st.booleans(),
        enable_pip_audit=st.booleans(),
        enable_mutmut=st.booleans(),
        mutmut_target_min=st.integers(min_value=0, max_value=20),
        mutmut_result_ratchet_enabled=st.booleans(),
        enable_semgrep=st.booleans(),
        enable_osv_scanner=st.booleans(),
        enable_trivy=st.booleans(),
        enable_sbom=st.booleans(),
        enable_license_check=st.booleans(),
        enable_secret_scanning=st.booleans(),
        architecture_tool=st.sampled_from(("tach", "import-linter")),
        enable_interrogate=st.booleans(),
        enable_markdownlint=st.booleans(),
        enable_yamllint=st.booleans(),
        enable_taplo=st.booleans(),
        enable_check_jsonschema=st.booleans(),
        diagnostic_artifacts_enabled=st.booleans(),
    )


@given(score=st.integers(min_value=-1_000, max_value=1_000))
def test_risk_label_returns_expected_band(score: int) -> None:
    """Risk labels stay stable across score bands."""
    label = risk_label(score)

    assert label in RISK_LABELS
    if score <= LOW_RISK_MAX:
        assert label == "low"
    elif score <= MODERATE_RISK_MAX:
        assert label == "moderate"
    elif score <= HIGH_RISK_MAX:
        assert label == "high"
    else:
        assert label == "critical"


@given(evidence=evidence_strategy(), config=config_strategy())
@settings(deadline=None, max_examples=100)
def test_debt_report_scores_stay_bounded_and_consistent(
    evidence: RepoEvidence,
    config: MaintainerConfig,
) -> None:
    """Generated debt reports keep bounded scores and matching labels."""
    with TemporaryDirectory() as directory:
        report = build_debt_report(evidence, config, log_dir=Path(directory))

    assert 0 <= report.score <= MAX_SCORE
    assert report.risk == risk_label(report.score)
    assert report.confidence in {"low", "medium", "high"}
    assert len(report.next_actions) == len(set(report.next_actions))
    assert report.categories
    for category in report.categories:
        assert 0 <= category.score <= MAX_SCORE
        assert category.status == risk_label(category.score)
        assert category.weight > 0
        assert category.evidence
        assert category.recommendations
