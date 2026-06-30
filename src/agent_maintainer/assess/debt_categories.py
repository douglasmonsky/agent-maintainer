"""Technical Debt Score category scoring."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.assess import debt_manifest, debt_security
from agent_maintainer.assess.models import DebtCategory, RepoEvidence
from agent_maintainer.config.schema import FRESH_STRICT_MODE, MaintainerConfig

LOW_RISK_MAX = 25
MODERATE_RISK_MAX = 50
HIGH_RISK_MAX = 75
MAX_SCORE = 100

REVIEWABILITY_BASE = 15
CHANGE_BUDGET_PENALTY = 20
SOURCE_LENGTH_PENALTY = 15
LARGE_SOURCE_PENALTY = 15
TRUNCATED_SCAN_PENALTY = 10
REVIEWABLE_LINE_BLOCK = 800
REVIEWABLE_FILE_BLOCK = 20
SOURCE_LENGTH_CAP = 450
LARGE_SOURCE_FILE_COUNT = 40
REVIEWABILITY_WEIGHT = 14

TESTS_BASE = 10
MISSING_REQUIRED_TESTS_PENALTY = 35
MISSING_TEST_TREE_PENALTY = 25
LOW_COVERAGE_PENALTY = 15
MIN_HEALTHY_COVERAGE = 80
TESTS_WEIGHT = 18

STYLE_BASE = 15
BASIC_TYPE_PENALTY = 15
HIGH_COMPLEXITY_PENALTY = 10
MISSING_WEMAKE_PENALTY = 10
RUFF_COMPLEXITY_CAP = 10
STYLE_WEIGHT = 12

ARCHITECTURE_BASE = 15
MISSING_TACH_PENALTY = 30
MISSING_IMPORT_LINTER_PENALTY = 25
ARCHITECTURE_WEIGHT = 14

SECURITY_WEIGHT = 14

DOCS_BASE = 10
MISSING_RELEVANT_DOCS_GATE_PENALTY = 10
DOCS_MIN_SCORE = 10
DOCS_WEIGHT = 10

DIAGNOSTICS_BASE = 15
DIAGNOSTICS_DISABLED_PENALTY = 20
MISSING_GUIDANCE_PENALTY = 12
DIAGNOSTICS_WEIGHT = 10

MUTATION_BASE = 25
MUTATION_DISABLED_PENALTY = 20
MUTATION_RATCHET_PENALTY = 25
HEALTHY_MUTATION_SCORE = 5
MUTATION_WEIGHT = 8

REVIEWABILITY_CHECKS = ("change", "file length", "suppression", "structure")
TEST_CHECKS = ("pytest", "coverage", "diff-cover", "test")
STYLE_CHECKS = ("ruff", "pyright", "pylint", "wemake", "xenon", "radon")
ARCHITECTURE_CHECKS = ("tach", "import-linter", "architecture")
SECURITY_CHECKS = ("audit", "secret", "bandit", "semgrep", "osv", "sbom", "license")
DOCS_CHECKS = ("interrogate", "markdown", "yaml", "toml", "jsonschema", "docs")
DIAGNOSTIC_CHECKS = ("doctor", "guidance", "artifact", "diagnostic")
MUTATION_CHECKS = ("mutmut", "mutation")


def build_debt_categories(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    *,
    log_dir: Path,
) -> tuple[DebtCategory, ...]:
    """Return transparent advisory debt categories."""

    manifest = debt_manifest.manifest_signals(log_dir)
    categories: list[DebtCategory] = []
    categories.append(_reviewability(evidence, config, manifest))
    categories.append(_tests_coverage(evidence, config, manifest))
    categories.append(_type_style(config, manifest))
    categories.append(_architecture(evidence, config, manifest))
    categories.append(_dependencies_security(evidence, config, manifest))
    categories.append(_docs_config(evidence, config, manifest))
    categories.append(_diagnostics(evidence, config, log_dir, manifest))
    categories.append(_mutation_ratchet(config, manifest))
    return tuple(categories)


def risk_label(score: int) -> str:
    """Return lower-is-better risk label."""

    if score <= LOW_RISK_MAX:
        return "low"
    if score <= MODERATE_RISK_MAX:
        return "moderate"
    if score <= HIGH_RISK_MAX:
        return "high"
    return "critical"


def _reviewability(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = REVIEWABILITY_BASE
    evidence_lines = [
        (
            f"change budget blocks {config.change_block_lines} lines / "
            f"{config.change_block_files} files"
        ),
        (
            f"file length caps {config.file_length_max_physical} physical / "
            f"{config.file_length_max_source} source lines"
        ),
        _scan_evidence(evidence),
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
    if evidence.scan_truncated:
        score += TRUNCATED_SCAN_PENALTY
    score = debt_manifest.with_manifest_penalty(
        score,
        evidence_lines,
        manifest,
        REVIEWABILITY_CHECKS,
    )
    return _category(
        "Reviewability",
        score,
        REVIEWABILITY_WEIGHT,
        evidence_lines,
        ("Keep change budgets tight enough for human review.",),
    )


def _tests_coverage(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = TESTS_BASE
    evidence_lines = [
        f"require_tests = {config.require_tests}",
        f"coverage floor = {config.coverage_fail_under}%",
        f"detected {evidence.test_files} Python test files",
    ]
    if _has_python_surface(evidence):
        if not config.require_tests:
            score += MISSING_REQUIRED_TESTS_PENALTY
        if not evidence.has_tests:
            score += MISSING_TEST_TREE_PENALTY
        if config.coverage_fail_under < MIN_HEALTHY_COVERAGE:
            score += LOW_COVERAGE_PENALTY
    else:
        evidence_lines.append("no Python surface detected; test debt not scored")
    score = debt_manifest.with_manifest_penalty(score, evidence_lines, manifest, TEST_CHECKS)
    return _category(
        "Tests and Coverage",
        score,
        TESTS_WEIGHT,
        evidence_lines,
        ("Keep total and changed-code coverage ratchets active.",),
    )


def _type_style(
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
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
    score = debt_manifest.with_manifest_penalty(score, evidence_lines, manifest, STYLE_CHECKS)
    return _category(
        "Type and Style",
        score,
        STYLE_WEIGHT,
        evidence_lines,
        ("Use strict style and type pressure where the repo can tolerate it.",),
    )


def _architecture(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
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
    score = debt_manifest.with_manifest_penalty(
        score,
        evidence_lines,
        manifest,
        ARCHITECTURE_CHECKS,
    )
    return _category(
        "Architecture Boundaries",
        score,
        ARCHITECTURE_WEIGHT,
        evidence_lines,
        ("Add an architecture contract once modules have real boundaries.",),
    )


def _dependencies_security(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    evidence_lines = debt_security.security_evidence(evidence, config)
    score = debt_security.security_score(evidence, config)
    score = debt_manifest.with_manifest_penalty(score, evidence_lines, manifest, SECURITY_CHECKS)
    return _category(
        "Dependencies and Security",
        score,
        SECURITY_WEIGHT,
        evidence_lines,
        ("Enable security gates only when repo evidence makes them relevant.",),
    )


def _docs_config(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = DOCS_BASE
    evidence_lines = [
        f"interrogate enabled = {config.enable_interrogate}",
        f"markdownlint enabled = {config.enable_markdownlint}",
        f"yamllint enabled = {config.enable_yamllint}",
        f"taplo enabled = {config.enable_taplo}",
    ]
    if _has_docs_config_surface(evidence):
        if evidence.yaml_files and not config.enable_yamllint:
            score += MISSING_RELEVANT_DOCS_GATE_PENALTY
        if evidence.toml_files and not config.enable_taplo:
            score += MISSING_RELEVANT_DOCS_GATE_PENALTY
    else:
        score = DOCS_MIN_SCORE
        evidence_lines.append("no docs/config surface detected; optional gates not scored")
    score = debt_manifest.with_manifest_penalty(score, evidence_lines, manifest, DOCS_CHECKS)
    return _category(
        "Docs and Config Hygiene",
        score,
        DOCS_WEIGHT,
        evidence_lines,
        ("Enable docs/config linting for formats that exist in the repo.",),
    )


def _diagnostics(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    log_dir: Path,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = DIAGNOSTICS_BASE
    manifest_present = (log_dir / debt_manifest.MANIFEST_JSON).exists()
    evidence_lines = [
        f"diagnostics enabled = {config.diagnostic_artifacts_enabled}",
        f"agent guidance present = {evidence.has_agent_guidance}",
        f"manifest present = {manifest_present}",
    ]
    if not config.diagnostic_artifacts_enabled:
        score += DIAGNOSTICS_DISABLED_PENALTY
    if not evidence.has_agent_guidance:
        score += MISSING_GUIDANCE_PENALTY
    score = debt_manifest.with_manifest_penalty(score, evidence_lines, manifest, DIAGNOSTIC_CHECKS)
    return _category(
        "Diagnostics Repair Loop",
        score,
        DIAGNOSTICS_WEIGHT,
        evidence_lines,
        ("Keep run-scoped diagnostics and generated agent guidance current.",),
    )


def _mutation_ratchet(
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = MUTATION_BASE
    evidence_lines = [
        f"mutmut enabled = {config.enable_mutmut}",
        f"mutation ratchet enabled = {config.mutmut_result_ratchet_enabled}",
        f"mutmut target minimum = {config.mutmut_target_min}",
    ]
    if config.enable_mutmut and config.mutmut_result_ratchet_enabled:
        score = HEALTHY_MUTATION_SCORE
    elif config.enable_mutmut:
        score += MUTATION_RATCHET_PENALTY
    else:
        score += MUTATION_DISABLED_PENALTY
    score = debt_manifest.with_manifest_penalty(score, evidence_lines, manifest, MUTATION_CHECKS)
    return _category(
        "Ratchets and Mutation Maturity",
        score,
        MUTATION_WEIGHT,
        evidence_lines,
        ("Use targeted mutation ratchets only after stable survivor counts.",),
    )


def _has_python_surface(evidence: RepoEvidence) -> bool:
    """Return whether evidence shows a Python repository surface."""

    return evidence.has_pyproject or evidence.source_files > 0 or evidence.test_files > 0


def _has_docs_config_surface(evidence: RepoEvidence) -> bool:
    """Return whether docs/config hygiene gates are relevant."""

    return evidence.yaml_files > 0 or evidence.toml_files > 0 or evidence.json_files > 0


def _scan_evidence(evidence: RepoEvidence) -> str:
    """Return concise scan provenance evidence."""

    suffix = " truncated" if evidence.scan_truncated else ""
    return f"evidence scan = {evidence.scan_source} ({evidence.scanned_files} files{suffix})"


def _category(
    name: str,
    score: int,
    weight: int,
    evidence: list[str],
    recommendations: tuple[str, ...],
) -> DebtCategory:
    bounded = _bounded(score)
    return DebtCategory(
        name=name,
        score=bounded,
        weight=weight,
        status=risk_label(bounded),
        evidence=tuple(evidence),
        recommendations=recommendations,
    )


def _bounded(score: int) -> int:
    """Return score constrained to public range."""

    return max(0, min(MAX_SCORE, score))
