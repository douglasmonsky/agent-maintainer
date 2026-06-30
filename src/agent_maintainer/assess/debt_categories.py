"""Technical Debt Score category scoring."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.assess.models import DebtCategory, RepoEvidence
from agent_maintainer.config.schema import FRESH_STRICT_MODE, MaintainerConfig

LOW_RISK_MAX = 25
MODERATE_RISK_MAX = 50
HIGH_RISK_MAX = 75
REVIEWABLE_LINE_BLOCK = 800
REVIEWABLE_FILE_BLOCK = 20
SOURCE_LENGTH_CAP = 450
MIN_HEALTHY_COVERAGE = 80
RUFF_COMPLEXITY_CAP = 10
LARGE_SOURCE_FILE_COUNT = 40
MAX_SCORE = 100
REVIEWABILITY_BASE = 15
CHANGE_BUDGET_PENALTY = 20
SOURCE_LENGTH_PENALTY = 15
LARGE_SOURCE_PENALTY = 15
REVIEWABILITY_WEIGHT = 14
TESTS_BASE = 10
MISSING_REQUIRED_TESTS_PENALTY = 35
MISSING_TEST_TREE_PENALTY = 25
LOW_COVERAGE_PENALTY = 15
TESTS_WEIGHT = 18
STYLE_BASE = 15
BASIC_TYPE_PENALTY = 15
HIGH_COMPLEXITY_PENALTY = 10
MISSING_WEMAKE_PENALTY = 10
STYLE_WEIGHT = 12
ARCHITECTURE_BASE = 15
MISSING_TACH_PENALTY = 30
MISSING_IMPORT_LINTER_PENALTY = 25
ARCHITECTURE_WEIGHT = 14
SECURITY_BASE = 75
SECURITY_GATE_CREDIT = 10
SECURITY_MIN_SCORE = 10
MISSING_PIP_AUDIT_PENALTY = 10
MISSING_SECRET_SCAN_PENALTY = 10
SECURITY_WEIGHT = 14
DOCS_BASE = 65
DOCS_GATE_CREDIT = 10
DOCS_MIN_SCORE = 10
DOCS_WEIGHT = 10
DIAGNOSTICS_BASE = 15
DIAGNOSTICS_DISABLED_PENALTY = 30
MISSING_MANIFEST_PENALTY = 10
DIAGNOSTICS_WEIGHT = 8
MUTATION_BASE = 45
RATCHET_CREDIT = 10
MUTATION_ENABLED_CREDIT = 10
MUTATION_TARGET_CREDIT = 10
MUTATION_RESULT_RATCHET_CREDIT = 10
MUTATION_WEIGHT = 10
MANIFEST_JSON = "manifest.json"


def build_debt_categories(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    *,
    log_dir: Path,
) -> tuple[DebtCategory, ...]:
    """Build all Technical Debt Score categories."""

    categories = [
        _reviewability(evidence, config),
        _tests_coverage(evidence, config),
        _type_style(config),
        _architecture(evidence, config),
        _dependencies_security(evidence, config),
        _docs_config(evidence, config),
        _diagnostics(config, log_dir),
        _mutation_ratchet(config),
    ]
    return tuple(categories)


def risk_label(score: int) -> str:
    """Return risk label for score."""

    if score <= LOW_RISK_MAX:
        return "low"
    if score <= MODERATE_RISK_MAX:
        return "moderate"
    if score <= HIGH_RISK_MAX:
        return "high"
    return "critical"


def _reviewability(evidence: RepoEvidence, config: MaintainerConfig) -> DebtCategory:
    score = REVIEWABILITY_BASE
    evidence_lines = [
        (
            f"change budget blocks at {config.change_block_lines} lines / "
            f"{config.change_block_files} files"
        ),
        (
            f"file length caps are {config.file_length_max_physical} physical / "
            f"{config.file_length_max_source} source lines"
        ),
    ]
    if (
        config.change_block_lines > REVIEWABLE_LINE_BLOCK
        or config.change_block_files > REVIEWABLE_FILE_BLOCK
    ):
        score += CHANGE_BUDGET_PENALTY
    if config.file_length_max_source > SOURCE_LENGTH_CAP:
        score += SOURCE_LENGTH_PENALTY
    if evidence.source_files >= LARGE_SOURCE_FILE_COUNT:
        score += LARGE_SOURCE_PENALTY
    return _category(
        "Reviewability",
        score,
        REVIEWABILITY_WEIGHT,
        evidence_lines,
        ("Keep change budgets tight enough for human review.",),
    )


def _tests_coverage(evidence: RepoEvidence, config: MaintainerConfig) -> DebtCategory:
    score = TESTS_BASE
    evidence_lines = [
        f"require_tests = {config.require_tests}",
        f"coverage floor = {config.coverage_fail_under}%",
        f"detected {evidence.test_files} Python test files",
    ]
    if not config.require_tests:
        score += MISSING_REQUIRED_TESTS_PENALTY
    if not evidence.has_tests:
        score += MISSING_TEST_TREE_PENALTY
    if config.coverage_fail_under < MIN_HEALTHY_COVERAGE:
        score += LOW_COVERAGE_PENALTY
    return _category(
        "Tests and Coverage",
        score,
        TESTS_WEIGHT,
        evidence_lines,
        ("Keep total and changed-code coverage ratchets active.",),
    )


def _type_style(config: MaintainerConfig) -> DebtCategory:
    score = STYLE_BASE
    evidence_lines = [
        f"pyright mode = {config.pyright_type_checking_mode}",
        f"Ruff complexity cap = {config.ruff_max_complexity}",
        f"wemake enabled = {config.enable_wemake}",
    ]
    if config.pyright_type_checking_mode == "basic":
        score += BASIC_TYPE_PENALTY
    if config.ruff_max_complexity > RUFF_COMPLEXITY_CAP:
        score += HIGH_COMPLEXITY_PENALTY
    if config.mode == FRESH_STRICT_MODE and not config.enable_wemake:
        score += MISSING_WEMAKE_PENALTY
    return _category(
        "Type and Style",
        score,
        STYLE_WEIGHT,
        evidence_lines,
        ("Use strict style/type pressure where the repo can tolerate it.",),
    )


def _architecture(evidence: RepoEvidence, config: MaintainerConfig) -> DebtCategory:
    score = ARCHITECTURE_BASE
    evidence_lines = [
        f"architecture tool = {config.architecture_tool}",
        f"tach.toml present = {evidence.has_tach}",
        f".importlinter present = {evidence.has_import_linter}",
    ]
    if config.architecture_tool == "tach" and not evidence.has_tach:
        score += MISSING_TACH_PENALTY
    if config.architecture_tool == "import-linter" and not evidence.has_import_linter:
        score += MISSING_IMPORT_LINTER_PENALTY
    return _category(
        "Architecture Boundaries",
        score,
        ARCHITECTURE_WEIGHT,
        evidence_lines,
        ("Document module boundaries before broad agent-authored changes.",),
    )


def _dependencies_security(
    evidence: RepoEvidence,
    config: MaintainerConfig,
) -> DebtCategory:
    enabled = sum(
        (
            config.enable_pip_audit,
            config.enable_secret_scanning,
            config.enable_osv_scanner,
            config.enable_trivy,
            config.enable_sbom,
            config.enable_license_check,
        ),
    )
    score = max(SECURITY_MIN_SCORE, SECURITY_BASE - enabled * SECURITY_GATE_CREDIT)
    evidence_lines = [
        f"dependency files present = {evidence.has_dependency_file}",
        f"lock file present = {evidence.has_lock_file}",
        f"enabled supply-chain/security gates = {enabled}",
    ]
    if evidence.has_dependency_file and not config.enable_pip_audit:
        score += MISSING_PIP_AUDIT_PENALTY
    if evidence.has_git and not config.enable_secret_scanning:
        score += MISSING_SECRET_SCAN_PENALTY
    return _category(
        "Dependencies and Security",
        score,
        SECURITY_WEIGHT,
        evidence_lines,
        ("Enable relevant security gates only where repo evidence justifies them.",),
    )


def _docs_config(evidence: RepoEvidence, config: MaintainerConfig) -> DebtCategory:
    enabled = sum(
        (
            config.enable_interrogate,
            config.enable_markdownlint,
            config.enable_yamllint,
            config.enable_taplo,
            config.enable_check_jsonschema,
        ),
    )
    score = max(DOCS_MIN_SCORE, DOCS_BASE - enabled * DOCS_GATE_CREDIT)
    file_counts = (
        f"YAML/TOML/JSON files = {evidence.yaml_files}/{evidence.toml_files}/{evidence.json_files}"
    )
    evidence_lines = [
        file_counts,
        f"enabled docs/config gates = {enabled}",
    ]
    return _category(
        "Docs and Config Hygiene",
        score,
        DOCS_WEIGHT,
        evidence_lines,
        ("Add schema/lint checks for config formats that matter to the repo.",),
    )


def _diagnostics(config: MaintainerConfig, log_dir: Path) -> DebtCategory:
    score = DIAGNOSTICS_BASE
    manifest_present = (log_dir / MANIFEST_JSON).exists()
    evidence_lines = [
        f"diagnostics enabled = {config.diagnostic_artifacts_enabled}",
        f"artifact directory = {config.diagnostic_artifacts_dir}",
        f"latest manifest present = {manifest_present}",
    ]
    if not config.diagnostic_artifacts_enabled:
        score += DIAGNOSTICS_DISABLED_PENALTY
    if not manifest_present:
        score += MISSING_MANIFEST_PENALTY
    return _category(
        "Diagnostics",
        score,
        DIAGNOSTICS_WEIGHT,
        evidence_lines,
        ("Keep run-scoped artifacts available for repair loops.",),
    )


def _mutation_ratchet(config: MaintainerConfig) -> DebtCategory:
    score = MUTATION_BASE
    evidence_lines = [
        f"ratchet enabled = {config.ratchet_enabled}",
        f"mutmut enabled = {config.enable_mutmut}",
        f"mutmut target minimum = {config.mutmut_target_min}",
        f"mutmut result ratchet enabled = {config.mutmut_result_ratchet_enabled}",
    ]
    if config.ratchet_enabled:
        score -= RATCHET_CREDIT
    if config.enable_mutmut:
        score -= MUTATION_ENABLED_CREDIT
    if config.mutmut_target_min > 0:
        score -= MUTATION_TARGET_CREDIT
    if config.mutmut_result_ratchet_enabled:
        score -= MUTATION_RESULT_RATCHET_CREDIT
    return _category(
        "Ratchets and Mutation Maturity",
        score,
        MUTATION_WEIGHT,
        evidence_lines,
        ("Use mutation ratchets only after survivor counts are stable.",),
    )


def _category(
    name: str,
    score: int,
    weight: int,
    evidence: list[str],
    recommendations: tuple[str, ...],
) -> DebtCategory:
    bounded = max(0, min(MAX_SCORE, score))
    return DebtCategory(
        name=name,
        score=bounded,
        weight=weight,
        status=risk_label(bounded),
        evidence=tuple(evidence),
        recommendations=recommendations,
    )
