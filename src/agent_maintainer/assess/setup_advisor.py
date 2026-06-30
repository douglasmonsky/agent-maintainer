"""Setup recommendation engine."""

from __future__ import annotations

from agent_maintainer.assess.models import (
    GateRecommendation,
    RepoEvidence,
    SetupAdvisorReport,
)

SMALL_REPO_FILE_LIMIT = 12
LARGE_SOURCE_FILE_COUNT = 40
HIGH_CONFIDENCE_SIGNALS = 5
MEDIUM_CONFIDENCE_SIGNALS = 3


def build_setup_report(evidence: RepoEvidence) -> SetupAdvisorReport:
    """Return recommended Agent Maintainer adoption settings."""
    track = _recommended_track(evidence)
    preset = _recommended_preset(evidence)
    return SetupAdvisorReport(
        target=evidence.target,
        track=track,
        preset=preset,
        confidence=_confidence(evidence),
        reasons=_reasons(evidence, track, preset),
        optional_gates=_optional_gates(evidence),
        agent_prompts=_agent_prompts(evidence),
        next_commands=_next_commands(track, preset),
        evidence=evidence,
    )


def _recommended_track(evidence: RepoEvidence) -> str:
    """Return core, agent, or hardening track."""
    if evidence.has_codex_hooks or evidence.has_claude_hooks or evidence.has_agent_guidance:
        return "agent"
    if evidence.has_ci and (evidence.yaml_files or evidence.toml_files or evidence.json_files):
        return "hardening"
    return "core"


def _recommended_preset(evidence: RepoEvidence) -> str:
    """Return initializer preset recommendation."""
    if (
        evidence.source_files <= SMALL_REPO_FILE_LIMIT
        and evidence.test_files <= SMALL_REPO_FILE_LIMIT
    ):
        return "strict-new-repo"
    if not evidence.has_tests or evidence.source_files >= LARGE_SOURCE_FILE_COUNT:
        return "legacy-ratchet"
    if evidence.has_agent_guidance:
        return "ai-agent-heavy"
    return "existing-app"


def _confidence(evidence: RepoEvidence) -> str:
    """Return confidence level based on available repo signals."""
    signal_count = sum(
        (
            evidence.has_pyproject,
            evidence.has_git,
            evidence.has_tests,
            evidence.has_src,
            evidence.has_ci,
            evidence.source_files > 0,
        ),
    )
    if signal_count >= HIGH_CONFIDENCE_SIGNALS:
        return "high"
    if signal_count >= MEDIUM_CONFIDENCE_SIGNALS:
        return "medium"
    return "low"


def _reasons(evidence: RepoEvidence, track: str, preset: str) -> tuple[str, ...]:
    """Return concise recommendation reasons."""
    reasons = [
        f"Recommended track `{track}` from current agent, CI, and config evidence.",
        f"Recommended preset `{preset}` from source/test size and adoption state.",
    ]
    if not evidence.has_agent_config:
        reasons.append("No `[tool.agent_maintainer]` config was found yet.")
    if evidence.has_tests:
        reasons.append(f"Detected {evidence.test_files} Python test files.")
    else:
        reasons.append("No test tree was detected; require_tests may need staged adoption.")
    if evidence.has_pre_commit:
        reasons.append("Detected pre-commit configuration for local verification.")
    return tuple(reasons)


def _optional_gates(evidence: RepoEvidence) -> tuple[GateRecommendation, ...]:
    """Return optional gate recommendations grounded in repo evidence."""
    gates: list[GateRecommendation] = []
    if evidence.has_dependency_file:
        gates.append(
            GateRecommendation(
                name="pip-audit",
                recommendation="enable",
                reason="Python dependency metadata is present.",
                config_key="enable_pip_audit",
                profiles=("full", "ci"),
            ),
        )
    if evidence.has_git:
        gates.append(
            GateRecommendation(
                name="secret-scan",
                recommendation="enable",
                reason="Git history/current tree can be scanned for accidental secrets.",
                config_key="enable_secret_scanning",
                profiles=("full", "ci", "security"),
            ),
        )
    if evidence.has_package_json or evidence.has_go_mod:
        gates.append(
            GateRecommendation(
                name="osv-scanner",
                recommendation="consider",
                reason="Non-Python ecosystem files are present.",
                config_key="enable_osv_scanner",
                profiles=("manual",),
            ),
        )
    if evidence.has_container_or_iac:
        gates.append(
            GateRecommendation(
                name="trivy",
                recommendation="consider",
                reason="Container or IaC files are present.",
                config_key="enable_trivy",
                profiles=("manual",),
            ),
        )
    if evidence.yaml_files:
        gates.append(
            GateRecommendation(
                name="yamllint",
                recommendation="consider",
                reason="YAML files are present.",
                config_key="enable_yamllint",
                profiles=("full",),
            ),
        )
    if evidence.toml_files:
        gates.append(
            GateRecommendation(
                name="taplo",
                recommendation="consider",
                reason="TOML files are present.",
                config_key="enable_taplo",
                profiles=("full",),
            ),
        )
    return tuple(gates)


def _agent_prompts(evidence: RepoEvidence) -> tuple[str, ...]:
    """Return follow-up prompts for an AI agent adopting the repo."""
    prompts = [
        "Identify generated, vendored, migration, and fixture paths that checks should ignore.",
        "Map source modules into likely architecture boundaries before enabling strict Tach.",
        "List commands that already represent the repo's real test, lint, type, and build gates.",
    ]
    if not evidence.has_tests:
        prompts.append("Find the smallest behavior surface where tests should be added first.")
    if evidence.source_files >= LARGE_SOURCE_FILE_COUNT:
        prompts.append("Group large folders by responsibility before tightening file-count gates.")
    return tuple(prompts)


def _next_commands(track: str, preset: str) -> tuple[str, ...]:
    """Return likely next setup commands."""
    return (
        f"agent-maintainer init --track {track} --preset {preset} --dry-run",
        f"agent-maintainer init --track {track} --preset {preset}",
        "agent-maintainer doctor",
        "agent-maintainer verify --profile precommit",
    )
