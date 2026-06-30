"""Security and dependency evidence for advisory debt scoring."""

from __future__ import annotations

from agent_maintainer.assess.models import RepoEvidence
from agent_maintainer.config.schema import MaintainerConfig

SECURITY_BASE = 20
MISSING_RELEVANT_SECURITY_GATE_PENALTY = 12
SECURITY_MIN_SCORE = 10


def security_score(evidence: RepoEvidence, config: MaintainerConfig) -> int:
    """Return evidence-normalized security score."""

    if not has_security_surface(evidence):
        return SECURITY_MIN_SCORE
    score = SECURITY_BASE
    if has_dependency_surface(evidence) and not config.enable_pip_audit:
        score += MISSING_RELEVANT_SECURITY_GATE_PENALTY
    if has_secret_surface(evidence) and not config.enable_secret_scanning:
        score += MISSING_RELEVANT_SECURITY_GATE_PENALTY
    if evidence.has_container_or_iac and not config.enable_trivy:
        score += MISSING_RELEVANT_SECURITY_GATE_PENALTY
    if config.enable_sbom:
        score -= MISSING_RELEVANT_SECURITY_GATE_PENALTY
    if config.enable_license_check:
        score -= MISSING_RELEVANT_SECURITY_GATE_PENALTY
    return score


def security_evidence(
    evidence: RepoEvidence,
    config: MaintainerConfig,
) -> list[str]:
    """Return security/dependency evidence lines."""

    lines = [
        f"dependency files present = {evidence.has_dependency_file}",
        f"lock file present = {evidence.has_lock_file}",
        f"package.json present = {evidence.has_package_json}",
        f"container/IaC surface = {evidence.has_container_or_iac}",
        f"pip-audit enabled = {config.enable_pip_audit}",
        f"secret scanning enabled = {config.enable_secret_scanning}",
        f"trivy enabled = {config.enable_trivy}",
        f"SBOM enabled = {config.enable_sbom}",
        f"license check enabled = {config.enable_license_check}",
    ]
    if not has_security_surface(evidence):
        lines.append("no dependency/security surface detected; optional gates not scored")
    return lines


def has_security_surface(evidence: RepoEvidence) -> bool:
    """Return whether security/dependency gates are relevant."""

    return any(
        (
            has_dependency_surface(evidence),
            has_secret_surface(evidence),
            evidence.has_container_or_iac,
        ),
    )


def has_dependency_surface(evidence: RepoEvidence) -> bool:
    """Return whether dependency scanning is relevant."""

    return any(
        (
            evidence.has_dependency_file,
            evidence.has_package_json,
            evidence.has_go_mod,
        ),
    )


def has_secret_surface(evidence: RepoEvidence) -> bool:
    """Return whether secret scanning is relevant."""

    return evidence.has_git or evidence.has_ci or evidence.has_agent_config
