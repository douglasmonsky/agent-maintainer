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
