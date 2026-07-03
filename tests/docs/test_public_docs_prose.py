"""Regression tests for important public documentation prose."""

from __future__ import annotations

from pathlib import Path


def normalized_text(path: str) -> str:
    """Return text normalized for phrase checks across line wrapping."""
    return " ".join(Path(path).read_text(encoding="utf-8").split())


def test_mutation_testing_doc_records_current_ratchet_posture() -> None:
    """Mutation testing docs should be readable and match current dogfood data."""
    text = normalized_text("docs/mutation-testing.md")

    expected = (
        "default product stance is targeted and ratcheted, not broad mutation everywhere.",
        "Mutation testing belongs in the `manual` profile:",
        "This repository dogfoods it only for targets that have proven stable enough to block.",
        "Terminal output stays summary-first: candidate, score, killed/total, "
        "survivors, suspicious/timeouts, promotion readiness, and artifact path.",
        "Blocking manual target set: `343/345` killed, `2` survivors, `99.42%` "
        "mutation score, `0` suspicious, and `0` timeout outcomes",
        "reduced from 124 to 39 survivors",
        "reduced from 270 to 11 survivors",
    )
    missing = [phrase for phrase in expected if phrase not in text]

    assert not missing, missing


def test_docsync_extraction_doc_preserves_boundary_wording() -> None:
    """DocSync extraction docs should keep clear source/generated boundaries."""
    text = normalized_text("docs/docsync-extraction.md")

    expected = (
        "DocSync is implemented as an extractable sibling package under `src/docsync/`.",
        "It must not import `agent_maintainer` or `archguard`; the boundary is enforced",
        "DocSync source truth lives under `.docsync/`.",
        "The trace file is human-authored, and generated files under `.docsync/out/` "
        "are rebuildable artifacts that should not be committed.",
    )
    missing = [phrase for phrase in expected if phrase not in text]

    assert not missing, missing


def test_important_public_docs_avoid_known_compressed_fragments() -> None:
    """Guard against compressed note fragments found during documentation audit."""
    text = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in ("docs/mutation-testing.md", "docs/docsync-extraction.md")
    )
    forbidden = (
        "product stance targeted ratcheted mutation everywhere",
        "keeps pre-commit normal CI responsive",
        "Use Mutmut's project config keep blocking surface intentional",
        "Promotion readiness advisory. candidate ready",
        "DocSync implemented extractable sibling package",
        "must not import `agent_maintainer` `archguard`",
        "trace file human-authored",
        "artifacts should not committed",
    )

    for fragment in forbidden:
        assert fragment not in text
