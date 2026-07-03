"""Tests README DocSync trace coverage."""

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
    "claim.readme.run_profiles",
    "claim.readme.supported_checks",
    "claim.readme.agent_repair_loop",
    "claim.readme.technical_debt_surface",
}

PUBLIC_DOC_OBJECTS = {
    "docs.quick_start.overview",
    "docs.onboarding_first_run.overview",
    "docs.diagnostics_repair_loop.overview",
    "docs.supported_scans.overview",
    "docs.ratcheting.overview",
    "docs.provider_status.overview",
}

PUBLIC_DOC_CLAIMS = {
    "claim.docs.quick_start_package_flow",
    "claim.docs.onboarding_first_run_repair_loop",
    "claim.docs.diagnostics_run_scoped_artifacts",
    "claim.docs.supported_scans_catalog",
    "claim.docs.ratcheting_command_surface",
    "claim.docs.provider_status_python_core",
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

    for claim_id in PUBLIC_DOC_CLAIMS:
        claim = claims[claim_id]
        assert claim["object"] in PUBLIC_DOC_OBJECTS
        assert claim["evidence"]
        for evidence_id in claim["evidence"]:
            assert evidence_id in evidence
