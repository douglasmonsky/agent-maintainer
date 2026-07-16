"""Public documentation contract for the experimental Java/Gradle provider."""

from __future__ import annotations

from tests.support.paths import REPO_ROOT


def read_doc(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def assert_phrases(relative: str, *phrases: str) -> None:
    text = read_doc(relative)
    normalized = " ".join(text.split())
    for phrase in phrases:
        expected = " ".join(phrase.split())
        assert expected in normalized, f"{relative} is missing {phrase!r}"


def test_java_provider_guide_covers_complete_experimental_contract() -> None:
    assert_phrases(
        "docs/java-gradle-provider.md",
        "# Experimental Java/Gradle Provider",
        "checked-in Gradle wrapper",
        "Recommended, Guided, or Full control",
        "80% line and 70% branch",
        "upward-only",
        "Spotless `ratchetFrom`",
        "native SpotBugs baseline",
        "`assess java-baseline create|inspect|prune`",
        "one real aggregate report",
        "separate labeled project facts",
        "at most one wrapper call",
        "at most two wrapper calls",
        "Linux and Windows",
        "context failures",
        "does not fall back to system Gradle",
        "Maven is not supported",
        "experimental",
    )


def test_first_touch_docs_route_users_to_current_java_capabilities() -> None:
    assert_phrases(
        "README.md",
        "experimental Java/Gradle provider",
        "docs/java-gradle-provider.md",
    )
    assert_phrases(
        "docs/provider-status.md",
        "exact upward-only JaCoCo thresholds",
        "live Linux/Windows Gradle fixtures",
        "Java/Gradle Provider Calibration",
    )
    assert_phrases(
        "docs/setup-advisor.md",
        "80% line and 70% branch",
        "real aggregate report",
        "per-project coverage labels",
    )
    assert_phrases(
        "docs/supported-scans-and-agent-use.md",
        "upward-only JaCoCo thresholds",
        "separate project coverage labels",
    )


def test_configuration_and_roadmap_docs_keep_status_and_topology_explicit() -> None:
    assert_phrases(
        "docs/configuration-reference.md",
        '"jacoco_ratchet_ref":"origin/main"',
        '"projects":[":"],',
        '"coverage_scope":"project"',
        '"coverage_label":":"',
    )
    assert_phrases(
        "docs/roadmap/overview.md",
        "Java/Gradle coverage and live-CI rollout is implemented",
        "remains experimental",
    )
    assert_phrases(
        "docs/provider-contribution-guide.md",
        "Experimental Java/Gradle Provider",
        "truthful coverage topology",
    )


def test_calibration_is_indexed_without_becoming_a_promotion_claim() -> None:
    assert_phrases(
        "docs/case-studies/README.md",
        "Java/Gradle provider calibration",
        "java-gradle-provider-calibration.md",
    )
    assert_phrases(
        "docs/case-studies/java-gradle-provider-calibration.md",
        "does not\npromote Java support beyond experimental status",
    )
