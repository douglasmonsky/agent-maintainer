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
TYPESCRIPT_LINT_SCRIPT_NAMES = frozenset(("eslint", "lint", "lint:js", "lint:ts"))
TYPESCRIPT_TYPECHECK_SCRIPT_NAMES = frozenset(
    ("check:types", "tsc", "type-check", "typecheck"),
)
TYPESCRIPT_TEST_SCRIPT_NAMES = frozenset(("jest", "test", "test:unit", "vitest"))
TYPESCRIPT_REPAIR_FACT_OUTPUT_GUIDANCE = (
    "prefer ESLint JSON, tsc --pretty false, Jest/Vitest JSON, and existing "
    "coverage-summary.json or lcov.info artifacts for repair facts"
)


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
    """Return core, agent, hardening, or inspect track."""
    if not _has_python_surface(evidence):
        return "inspect"
    if evidence.has_codex_hooks or evidence.has_claude_hooks or evidence.has_agent_guidance:
        return "agent"
    if evidence.has_ci and (evidence.yaml_files or evidence.toml_files or evidence.json_files):
        return "hardening"
    return "core"


def _recommended_preset(evidence: RepoEvidence) -> str:
    """Return initializer preset recommendation."""
    if not _has_python_surface(evidence):
        return "manual-review"
    if (
        evidence.source_files <= SMALL_REPO_FILE_LIMIT
        and evidence.test_files <= SMALL_REPO_FILE_LIMIT
    ):
        return "strict-new-repo"
    if not evidence.has_tests and evidence.source_files >= LARGE_SOURCE_FILE_COUNT:
        return "legacy-ratchet"
    if evidence.has_agent_guidance:
        return "ai-agent-heavy"
    return "existing-app"


def _confidence(evidence: RepoEvidence) -> str:
    """Return confidence level based on available repo signals."""
    if not _has_python_surface(evidence) or evidence.scan_truncated:
        return "low"
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
        f"Evidence scan `{evidence.scan_source}` inspected {evidence.scanned_files} files.",
    ]
    if evidence.scan_truncated:
        reasons.append("Evidence scan was truncated; review recommendations manually.")
    if not _has_python_surface(evidence):
        reasons.append(
            "No Python package or source files detected; inspect repo type before init.",
        )
        return tuple(reasons)
    if not evidence.has_agent_config:
        reasons.append("No `[tool.agent_maintainer]` config found yet.")
    if evidence.has_tests:
        reasons.append(f"Detected {evidence.test_files} Python test files.")
    else:
        reasons.append("No test tree detected; require_tests may need staged adoption.")
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
    if evidence.has_package_json:
        gates.append(
            GateRecommendation(
                name="osv-scanner",
                recommendation="consider",
                reason="Non-Python ecosystem files are present.",
                config_key="enable_osv_scanner",
                profiles=("manual",),
            ),
        )
    if _typescript_script_signals(evidence):
        gates.append(
            GateRecommendation(
                name="typescript-provider",
                recommendation="consider",
                reason=(
                    "package.json exposes lint/typecheck/test scripts that can be "
                    "mapped to explicit TypeScript provider commands; "
                    f"{TYPESCRIPT_REPAIR_FACT_OUTPUT_GUIDANCE}."
                ),
                config_key="enable_typescript",
                profiles=("precommit", "full", "ci"),
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
    if not _has_python_surface(evidence):
        return (
            "Identify the repo language, package manager, test command, and CI command.",
            "Confirm Agent Maintainer is appropriate before writing starter files.",
            "Run only a dry-run initializer until Python surfaces are confirmed.",
        )
    prompts = [
        "Identify generated, vendored, migration, and fixture paths checks should ignore.",
        "Map source modules into likely architecture boundaries before enabling strict Tach.",
        "List commands that are already the repo's real test, lint, type, and build gates.",
    ]
    if not evidence.has_tests:
        prompts.append("Find the smallest behavior surface where tests should be added first.")
    if evidence.source_files >= LARGE_SOURCE_FILE_COUNT:
        prompts.append(
            "Group large folders by responsibility before tightening file-count gates.",
        )
    if _typescript_script_signals(evidence):
        prompts.append(
            "Map existing package.json scripts to explicit TypeScript provider "
            "commands; do not guess package manager.",
        )
        prompts.append(
            f"When mapping TypeScript scripts, {TYPESCRIPT_REPAIR_FACT_OUTPUT_GUIDANCE}.",
        )
    return tuple(prompts)


def _next_commands(track: str, preset: str) -> tuple[str, ...]:
    """Return likely next setup commands."""
    if track == "inspect":
        return (
            "agent-maintainer assess setup --target . --json",
            "agent-maintainer init --track core --dry-run",
            "Ask an agent to identify the repo language, test command, and generated paths.",
        )
    return (
        f"agent-maintainer init --track {track} --preset {preset} --dry-run",
        f"agent-maintainer init --track {track} --preset {preset}",
        "agent-maintainer doctor",
        "agent-maintainer verify --profile precommit",
    )


def _has_python_surface(evidence: RepoEvidence) -> bool:
    """Return whether evidence looks like a Python repository."""
    return evidence.has_pyproject or evidence.source_files > 0 or evidence.test_files > 0


def _typescript_script_signals(evidence: RepoEvidence) -> tuple[str, ...]:
    """Return package scripts that suggest explicit TypeScript provider commands."""
    return tuple(
        script_name
        for script_name in evidence.package_scripts
        if _is_typescript_script_signal(script_name)
    )


def _is_typescript_script_signal(script_name: str) -> bool:
    """Return whether script name maps to a TypeScript provider command kind."""
    normalized = script_name.lower()
    return (
        normalized in TYPESCRIPT_LINT_SCRIPT_NAMES
        or normalized in TYPESCRIPT_TYPECHECK_SCRIPT_NAMES
        or normalized in TYPESCRIPT_TEST_SCRIPT_NAMES
    )
