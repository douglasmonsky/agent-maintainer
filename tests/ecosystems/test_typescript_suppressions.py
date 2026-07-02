"""Tests TypeScript JavaScript suppression classification."""

from __future__ import annotations

from agent_maintainer.ecosystems.typescript import suppressions


def test_ts_suppressions_classify_broad_markers() -> None:
    """Broad TypeScript JavaScript suppressions are visible."""
    findings = suppressions.classify_line("// eslint-disable")
    ts_ignore = suppressions.classify_line("// @ts-ignore")
    ts_nocheck = suppressions.classify_line("// @ts-nocheck")

    assert findings[0].kind == "eslint-disable"
    assert findings[0].broad is True
    assert ts_ignore[0].broad is True
    assert ts_nocheck[0].broad is True


def test_ts_suppressions_classify_narrow_markers() -> None:
    """Rule-specific and coverage suppressions are tracked as narrow."""
    eslint = suppressions.classify_line("// eslint-disable-next-line no-console")
    expected = suppressions.classify_line("// @ts-expect-error legacy type")
    istanbul = suppressions.classify_line("/* istanbul ignore next */")
    c8 = suppressions.classify_line("// c8 ignore next")

    assert eslint[0].broad is False
    assert expected[0].kind == "ts-expect-error"
    assert istanbul[0].kind == "istanbul-ignore"
    assert c8[0].kind == "c8-ignore"


def test_ts_suppressions_ignore_normal_comments() -> None:
    """Normal comments do not become suppression findings."""
    assert suppressions.classify_line("// regular comment") == ()
