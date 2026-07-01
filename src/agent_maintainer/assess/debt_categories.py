"""Technical Debt Score category scoring."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.assess import debt_category_constants as constants
from agent_maintainer.assess import debt_manifest, debt_security
from agent_maintainer.assess.models import DebtCategory, RepoEvidence
from agent_maintainer.config.schema import FRESH_STRICT_MODE, MaintainerConfig


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

    if score <= constants.LOW_RISK_MAX:
        return "low"
    if score <= constants.MODERATE_RISK_MAX:
        return "moderate"
    if score <= constants.HIGH_RISK_MAX:
        return "high"
    return "critical"


def _reviewability(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.REVIEWABILITY_BASE
    evidence_lines = [
        (
            f"change budget blocks {config.change_block_lines} lines / "
            f"{config.change_block_files} files"
        ),
        (
            f"file length caps {config.file_length_max_physical} physical / "
            f"{config.file_length_max_source} source lines"
        ),
        f"folder file-count warning/block = {config.folder_file_warn}/{config.folder_file_block}",
        _scan_evidence(evidence),
    ]
    if (
        config.change_block_lines > constants.REVIEWABLE_LINE_BLOCK
        or config.change_block_files > constants.REVIEWABLE_FILE_BLOCK
    ):
        score += constants.CHANGE_BUDGET_PENALTY
    if config.file_length_max_source > constants.SOURCE_LENGTH_CAP:
        score += constants.SOURCE_LENGTH_PENALTY
    elif config.file_length_max_source <= constants.EXCELLENT_SOURCE_LENGTH_CAP:
        evidence_lines.append("excellent source length cap active")
    if evidence.scan_truncated:
        score += constants.TRUNCATED_SCAN_PENALTY
    score = debt_manifest.with_manifest_penalty(
        score,
        evidence_lines,
        manifest,
        constants.REVIEWABILITY_CHECKS,
    )
    return _category(
        "Reviewability",
        score,
        constants.REVIEWABILITY_WEIGHT,
        evidence_lines,
        ("Keep change budgets tight enough for human review.",),
    )


def _tests_coverage(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.TESTS_BASE
    evidence_lines = [
        f"require_tests = {config.require_tests}",
        f"coverage floor = {config.coverage_fail_under}%",
        f"diff coverage floor = {config.diff_cover_fail_under}%",
        f"detected {evidence.test_files} Python test files",
    ]
    if _has_python_surface(evidence):
        if not config.require_tests:
            score += constants.MISSING_REQUIRED_TESTS_PENALTY
        if not evidence.has_tests:
            score += constants.MISSING_TEST_TREE_PENALTY
        if config.coverage_fail_under < constants.MIN_HEALTHY_COVERAGE:
            score += constants.LOW_COVERAGE_PENALTY
        elif config.coverage_fail_under >= constants.EXCELLENT_COVERAGE:
            evidence_lines.append("excellent coverage floor active")
        if config.diff_cover_fail_under >= constants.EXCELLENT_COVERAGE:
            evidence_lines.append("excellent changed-code coverage floor active")
    else:
        evidence_lines.append("no Python surface detected; test debt not scored")
    score = debt_manifest.with_manifest_penalty(
        score, evidence_lines, manifest, constants.TEST_CHECKS
    )
    return _category(
        "Tests and Coverage",
        score,
        constants.TESTS_WEIGHT,
        evidence_lines,
        ("Keep total and changed-code coverage ratchets active.",),
    )


def _type_style(
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.STYLE_BASE
    evidence_lines = [
        f"pyright mode = {config.pyright_type_checking_mode}",
        f"strict Pyright ratchet enabled = {config.pyright_strict_ratchet_enabled}",
        f"Ruff complexity cap = {config.ruff_max_complexity}",
        f"wemake enabled = {config.enable_wemake}",
    ]
    if config.pyright_type_checking_mode == "basic":
        score += constants.BASIC_TYPE_PENALTY
    if config.pyright_strict_ratchet_enabled:
        score = max(0, score - constants.STRICT_TYPE_REDUCTION)
    if config.ruff_max_complexity > constants.RUFF_COMPLEXITY_CAP:
        score += constants.HIGH_COMPLEXITY_PENALTY
    if config.mode == FRESH_STRICT_MODE and not config.enable_wemake:
        score += constants.MISSING_WEMAKE_PENALTY
    score = debt_manifest.with_manifest_penalty(
        score, evidence_lines, manifest, constants.STYLE_CHECKS
    )
    return _category(
        "Type and Style",
        score,
        constants.STYLE_WEIGHT,
        evidence_lines,
        ("Use strict style and type pressure where the repo can tolerate it.",),
    )


def _architecture(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.ARCHITECTURE_BASE
    evidence_lines = [
        f"architecture tool = {config.architecture_tool}",
        f"tach.toml present = {evidence.has_tach}",
        f".importlinter present = {evidence.has_import_linter}",
    ]
    if config.architecture_tool == "tach" and not evidence.has_tach:
        score += constants.MISSING_TACH_PENALTY
    elif config.architecture_tool == "tach" and evidence.has_tach:
        evidence_lines.append("tach architecture contract present")
    if config.architecture_tool == "import-linter" and not evidence.has_import_linter:
        score += constants.MISSING_IMPORT_LINTER_PENALTY
    score = debt_manifest.with_manifest_penalty(
        score,
        evidence_lines,
        manifest,
        constants.ARCHITECTURE_CHECKS,
    )
    return _category(
        "Architecture Boundaries",
        score,
        constants.ARCHITECTURE_WEIGHT,
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
    score = debt_manifest.with_manifest_penalty(
        score, evidence_lines, manifest, constants.SECURITY_CHECKS
    )
    return _category(
        "Dependencies and Security",
        score,
        constants.SECURITY_WEIGHT,
        evidence_lines,
        ("Enable security gates only when repo evidence makes them relevant.",),
    )


def _docs_config(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.DOCS_BASE
    evidence_lines = [
        f"interrogate enabled = {config.enable_interrogate}",
        f"markdownlint enabled = {config.enable_markdownlint}",
        f"yamllint enabled = {config.enable_yamllint}",
        f"taplo enabled = {config.enable_taplo}",
    ]
    if _has_docs_config_surface(evidence):
        if evidence.yaml_files and not config.enable_yamllint:
            score += constants.MISSING_RELEVANT_DOCS_GATE_PENALTY
        if evidence.toml_files and not config.enable_taplo:
            score += constants.MISSING_RELEVANT_DOCS_GATE_PENALTY
        if config.enable_interrogate and config.enable_markdownlint:
            evidence_lines.append("documentation gates active")
        if config.enable_yamllint and config.enable_taplo:
            evidence_lines.append("YAML/TOML config gates active")
    else:
        score = constants.DOCS_MIN_SCORE
        evidence_lines.append("no docs/config surface detected; optional gates not scored")
    score = debt_manifest.with_manifest_penalty(
        score, evidence_lines, manifest, constants.DOCS_CHECKS
    )
    return _category(
        "Docs and Config Hygiene",
        score,
        constants.DOCS_WEIGHT,
        evidence_lines,
        ("Enable docs/config linting for formats that exist in the repo.",),
    )


def _diagnostics(
    evidence: RepoEvidence,
    config: MaintainerConfig,
    log_dir: Path,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.DIAGNOSTICS_BASE
    manifest_present = (log_dir / debt_manifest.MANIFEST_JSON).exists()
    evidence_lines = [
        f"diagnostics enabled = {config.diagnostic_artifacts_enabled}",
        f"agent guidance present = {evidence.has_agent_guidance}",
        f"manifest present = {manifest_present}",
        f"run history limit = {config.diagnostic_run_history_limit}",
    ]
    if not config.diagnostic_artifacts_enabled:
        score += constants.DIAGNOSTICS_DISABLED_PENALTY
    if not evidence.has_agent_guidance:
        score += constants.MISSING_GUIDANCE_PENALTY
    score = debt_manifest.with_manifest_penalty(
        score, evidence_lines, manifest, constants.DIAGNOSTIC_CHECKS
    )
    return _category(
        "Diagnostics Repair Loop",
        score,
        constants.DIAGNOSTICS_WEIGHT,
        evidence_lines,
        ("Keep run-scoped diagnostics and generated agent guidance current.",),
    )


def _mutation_ratchet(
    config: MaintainerConfig,
    manifest: debt_manifest.ManifestSignals,
) -> DebtCategory:
    score = constants.MUTATION_BASE
    evidence_lines = [
        f"mutmut enabled = {config.enable_mutmut}",
        f"mutation ratchet enabled = {config.mutmut_result_ratchet_enabled}",
        f"mutmut target minimum = {config.mutmut_target_min}",
    ]
    if config.enable_mutmut and config.mutmut_result_ratchet_enabled:
        score = constants.HEALTHY_MUTATION_SCORE
    elif config.enable_mutmut:
        score += constants.MUTATION_RATCHET_PENALTY
    else:
        score += constants.MUTATION_DISABLED_PENALTY
    score = debt_manifest.with_manifest_penalty(
        score, evidence_lines, manifest, constants.MUTATION_CHECKS
    )
    return _category(
        "Ratchets and Mutation Maturity",
        score,
        constants.MUTATION_WEIGHT,
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

    return max(0, min(constants.MAX_SCORE, score))
