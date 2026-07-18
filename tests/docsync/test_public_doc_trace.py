"""Tests public DocSync trace coverage."""

from __future__ import annotations

from pathlib import Path

import yaml

README_OBJECTS = {
    "docs.readme.overview",
    "docs.readme.quick_start",
    "docs.readme.adoption_tracks",
    "docs.readme.run_profiles",
    "docs.readme.supported_checks",
    "docs.readme.agent_loop",
    "docs.readme.technical_debt",
}

README_CLAIMS = {
    "claim.readme.package_identity",
    "claim.readme.quick_start_flow",
    "claim.readme.adoption_tracks",
    "claim.readme.run_profiles",
    "claim.readme.supported_checks",
    "claim.readme.agent_repair_loop",
    "claim.readme.technical_debt_surface",
}

PUBLIC_DOC_OBJECTS = {
    "docs.agent_maintainer_setup_skill.overview",
    "docs.quick_start.overview",
    "docs.onboarding_first_run.overview",
    "docs.diagnostics_repair_loop.overview",
    "docs.supported_scans.overview",
    "docs.ratcheting.overview",
    "docs.provider_status.overview",
    "docs.java_gradle_provider.overview",
    "docs.java_gradle_calibration.overview",
    "docs.typescript_provider.overview",
    "docs.typescript_maturation.overview",
    "docs.agent_client_hooks.overview",
    "docs.context_compression.overview",
    "docs.release_checklist.overview",
    "docs.architecture_policy.overview",
    "docs.agent_maintainer_guidance.overview",
    "docs.setup_advisor.overview",
    "docs.technical_debt_score.overview",
    "docs.mutation_testing.overview",
    "docs.context_safety.overview",
    "docs.multi_ecosystem_reviewability_policy.overview",
    "docs.release_index.overview",
    "docs.release_0_1_0b6_candidate.overview",
    "docs.upgrade_0_1_0b6.overview",
}

PUBLIC_DOC_CLAIMS = {
    "claim.docs.agent_maintainer_setup_dual_client",
    "claim.docs.quick_start_package_flow",
    "claim.docs.onboarding_first_run_repair_loop",
    "claim.docs.diagnostics_run_scoped_artifacts",
    "claim.docs.supported_scans_catalog",
    "claim.docs.ratcheting_command_surface",
    "claim.docs.provider_status_python_core",
    "claim.docs.provider_status_no_active_go",
    "claim.docs.java_provider_foundation",
    "claim.docs.java_provider_coverage_rollout",
    "claim.docs.java_provider_calibration",
    "claim.docs.typescript_provider_explicit_commands",
    "claim.docs.typescript_provider_repair_facts",
    "claim.docs.typescript_provider_unsupported_surface",
    "claim.docs.typescript_maturation_fixture_evidence",
    "claim.docs.typescript_maturation_real_repo_evidence",
    "claim.docs.agent_hooks_install_surface",
    "claim.docs.context_compression_safety",
    "claim.docs.release_checklist_packaging",
    "claim.docs.architecture_policy_tach",
    "claim.docs.agent_guidance_compact_sidecar",
    "claim.docs.setup_advisor_recommendations",
    "claim.docs.technical_debt_score_advisory",
    "claim.docs.mutation_testing_targeted_workflow",
    "claim.docs.context_safety_pointer_first_packs",
    "claim.docs.multi_ecosystem_reviewability_advisory",
    "claim.docs.release_index_state",
    "claim.docs.release_0_1_0b6_candidate_truth",
    "claim.docs.upgrade_0_1_0b6_safe_adoption",
}

PUBLIC_DOC_EVIDENCE = {
    "evidence.typescript.package_workspace_detection_tests",
    "evidence.typescript.knip_fact_tests",
    "evidence.typescript.knip_summary_tests",
    "evidence.typescript.knip_external_fixtures",
}

ACTIVE_DOC_PATHS = {
    "README.md",
    "docs/agent-client-hooks.md",
    "docs/agent-maintainer-guidance.md",
    "docs/agent-maintainer-setup-skill.md",
    "docs/architecture-policy.md",
    "docs/change-plans.md",
    "docs/codex-hooks.md",
    "docs/cohesive-change-overrides.md",
    "docs/cohesive-change-plans.md",
    "docs/config-metadata.md",
    "docs/context-compression.md",
    "docs/context-safety.md",
    "docs/diagnostics-repair-loop.md",
    "docs/docsync-extraction.md",
    "docs/fresh-strict.md",
    "docs/legacy-ratchet.md",
    "docs/multi-ecosystem-reviewability-policy.md",
    "docs/mutation-testing.md",
    "docs/onboarding-first-run.md",
    "docs/optional-gates.md",
    "docs/provider-contribution-guide.md",
    "docs/provider-status.md",
    "docs/java-gradle-provider.md",
    "docs/quick-start.md",
    "docs/ratcheting.md",
    "docs/release-checklist.md",
    "docs/setup-advisor.md",
    "docs/structure-cohesion.md",
    "docs/supported-scans-and-agent-use.md",
    "docs/team-policy-templates.md",
    "docs/technical-debt-score.md",
    "docs/test-intelligence.md",
    "docs/tool-map.md",
    "docs/troubleshooting.md",
    "docs/typescript-javascript-provider.md",
    "docs/case-studies/README.md",
    "docs/case-studies/context-safe-ratchet-repair.md",
    "docs/case-studies/future-call-roi-loop.md",
    "docs/case-studies/java-gradle-provider-calibration.md",
    "docs/case-studies/split-large-legacy-file.md",
    "docs/case-studies/typescript-provider-maturation.md",
    "docs/releases/0.1.0b4.md",
    "docs/releases/0.1.0b5.md",
    "docs/releases/0.1.0b6.md",
    "docs/releases/README.md",
    "docs/upgrading-to-0.1.0b6.md",
}


def test_readme_public_claims_are_traced() -> None:
    """README onboarding claims stay connected to trace evidence."""

    trace = yaml.safe_load(Path(".docsync/trace.yml").read_text(encoding="utf-8"))
    objects = trace["objects"]
    claims = trace["claims"]
    evidence = trace["evidence"]

    assert set(objects) >= README_OBJECTS
    assert set(claims) >= README_CLAIMS

    for claim_id in README_CLAIMS:
        claim = claims[claim_id]
        assert claim["object"].startswith("docs.readme.")
        assert claim["evidence"]
        for evidence_id in claim["evidence"]:
            assert evidence_id in evidence


def test_public_docs_claims_are_traced() -> None:
    """High-value public docs stay connected to implementation evidence."""

    trace = yaml.safe_load(Path(".docsync/trace.yml").read_text(encoding="utf-8"))
    objects = trace["objects"]
    claims = trace["claims"]
    evidence = trace["evidence"]

    assert set(objects) >= PUBLIC_DOC_OBJECTS
    assert set(claims) >= PUBLIC_DOC_CLAIMS
    assert set(evidence) >= PUBLIC_DOC_EVIDENCE

    for claim_id in PUBLIC_DOC_CLAIMS:
        claim = claims[claim_id]
        assert claim["object"] in PUBLIC_DOC_OBJECTS
        assert claim["evidence"]
        for evidence_id in claim["evidence"]:
            assert evidence_id in evidence


def test_active_docs_have_trace_overview_coverage() -> None:
    """Active docs are listed in DocSync and have live overview objects."""
    trace = yaml.safe_load(Path(".docsync/trace.yml").read_text(encoding="utf-8"))
    documents = trace["documents"]
    objects = trace["objects"]

    traced_paths = {document["path"] for document in documents.values()}
    assert traced_paths >= ACTIVE_DOC_PATHS

    overview_paths = {
        obj["path"] for object_id, obj in objects.items() if object_id.endswith(".overview")
    }
    assert overview_paths >= ACTIVE_DOC_PATHS


def test_public_doc_objects_have_claim_coverage() -> None:
    """High-value public doc objects have at least one evidence-backed claim."""
    trace = yaml.safe_load(Path(".docsync/trace.yml").read_text(encoding="utf-8"))
    objects = trace["objects"]
    claims = trace["claims"]
    claimed_objects = {claim["object"] for claim in claims.values()}

    assert set(objects) >= PUBLIC_DOC_OBJECTS
    assert PUBLIC_DOC_OBJECTS - claimed_objects == set()


def test_active_doc_overviews_have_claim_coverage() -> None:
    """Every active doc overview path has evidence-backed claim coverage."""
    trace = yaml.safe_load(Path(".docsync/trace.yml").read_text(encoding="utf-8"))
    objects = trace["objects"]
    claims = trace["claims"]

    claimed_paths = {
        objects[claim["object"]]["path"]
        for claim in claims.values()
        if claim["object"] in objects
        and claim["object"].endswith(".overview")
        and claim.get("evidence")
    }

    assert ACTIVE_DOC_PATHS - claimed_paths == set()
