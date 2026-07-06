"""Regression tests for the Future-Call ROI loop dogfood case study."""

from __future__ import annotations

from pathlib import Path

CASE_STUDY = Path("docs/case-studies/future-call-roi-loop.md")
CASE_STUDY_INDEX = Path("docs/case-studies/README.md")


def _normalized_text(path: Path) -> str:
    """Return Markdown text with whitespace normalized for phrase checks."""

    return " ".join(path.read_text(encoding="utf-8").split())


# docsync:evidence.start evidence.case_studies.future_call_roi_loop_tests
def test_future_call_roi_case_study_has_required_sections() -> None:
    """Phase 160 case study keeps the required ROI structure."""

    text = CASE_STUDY.read_text(encoding="utf-8")

    required_headings = (
        "## Baseline Workflow",
        "## New Workflow",
        "## Evidence",
        "## Cost Impact",
        "## Quality Impact",
        "## Speed Impact",
        "## Model-Tier Routing Decision",
        "## Primitive Evaluation",
        "## Remaining Gaps",
        "## Agent Lesson",
    )

    for heading in required_headings:
        assert heading in text


def test_future_call_roi_case_study_records_measured_evidence() -> None:
    """Case study includes measured facts instead of unsupported claims."""

    normalized = _normalized_text(CASE_STUDY)

    required_phrases = (
        "Technical debt score `6/100` (`low`) with `high` confidence",
        "143 events across 18 files",
        "42 generated/cache artifacts",
        "structured repair-fact coverage was `0.0%`",
        "1,047 errors versus 889 allowed, delta `+158`",
        "Full profile recorded 30 checks, all passed.",
        "No pre-phase run captured an apples-to-apples token, dollar, or elapsed-time baseline",
    )

    missing = [phrase for phrase in required_phrases if phrase not in normalized]
    assert not missing, f"missing measured evidence: {missing!r}"


def test_future_call_roi_case_study_keeps_routing_limits_explicit() -> None:
    """Case study does not claim cheap-worker routing is proven."""

    normalized = _normalized_text(CASE_STUDY)

    required_phrases = (
        "does not yet support automatically routing easy tasks to cheaper workers",
        "Token spend, API dollars, and chat narration volume were not captured",
        "wait command runtime events so PR wait-poll counts become measurable",
        "Use the ROI loop as a triage aid, not an autonomy proof.",
    )

    missing = [phrase for phrase in required_phrases if phrase not in normalized]
    assert not missing, f"missing routing-limit wording: {missing!r}"


def test_case_study_index_links_future_call_roi_loop() -> None:
    """Measured case-study index links the Phase 160 page."""

    text = CASE_STUDY_INDEX.read_text(encoding="utf-8")

    assert "[Future-Call ROI loop dogfood](future-call-roi-loop.md)" in text


# docsync:evidence.end evidence.case_studies.future_call_roi_loop_tests
