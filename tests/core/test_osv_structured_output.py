"""Tests bounded OSV Scanner v2 artifact summaries."""

from __future__ import annotations

from agent_maintainer.core import structured_security

OSV_SUMMARY_LINE_LIMIT = 50


# docsync:evidence.start evidence.typescript.osv_summary_tests
def test_osv_summary_uses_nested_version_and_alias_group() -> None:
    """Compact output uses the current package shape without alias duplicates."""

    payload = {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "demo",
                            "version": "2",
                        },
                        "version": "1",
                        "vulnerabilities": [
                            {
                                "id": "CVE-1",
                                "aliases": ["GHSA-1"],
                                "summary": "demo issue",
                            },
                            {"id": "GHSA-1", "aliases": ["CVE-1"]},
                        ],
                        "groups": [{"ids": ["GHSA-1", "CVE-1"]}],
                    }
                ],
            }
        ]
    }

    assert structured_security.summarize_osv_payload(payload) == (
        "npm/demo 2: CVE-1 (GHSA-1); source: package-lock.json; demo issue"
    )


def test_osv_summary_reserves_final_line_for_omission_marker() -> None:
    """The fiftieth compact line reports every omitted vulnerability."""

    summary = structured_security.summarize_osv_payload(_payload_with_findings(51))

    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == OSV_SUMMARY_LINE_LIMIT
    assert lines[-1] == (
        "... 2 more OSV vulnerabilities omitted. See .verify-logs/osv-scanner.json"
    )


def test_osv_summary_counts_findings_beyond_the_parser_cap() -> None:
    """The omission count includes valid findings beyond parser retention."""

    summary = structured_security.summarize_osv_payload(_payload_with_findings(501))

    assert summary is not None
    lines = summary.splitlines()
    assert len(lines) == OSV_SUMMARY_LINE_LIMIT
    assert lines[-1] == (
        "... 452 more OSV vulnerabilities omitted. See .verify-logs/osv-scanner.json"
    )


def test_osv_invalid_payload_has_no_summary() -> None:
    """Unsupported JSON keeps the bounded raw-output fallback available."""

    assert structured_security.summarize_osv_payload({}) is None


def _payload_with_findings(count: int) -> dict[str, object]:
    return {
        "results": [
            {
                "source": {"path": "package-lock.json", "type": "lockfile"},
                "packages": [
                    {
                        "package": {
                            "ecosystem": "npm",
                            "name": "demo",
                            "version": "1",
                        },
                        "vulnerabilities": [{"id": f"OSV-{index:03d}"} for index in range(count)],
                    }
                ],
            }
        ]
    }


# docsync:evidence.end evidence.typescript.osv_summary_tests
