"""Tests expanded structured artifact summaries."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.core import reporting as maintainer_reporting
from agent_maintainer.core import structured_artifacts, structured_pytest, structured_security

PYTEST_INT_FALLBACK = 7
SECURITY_INT_FALLBACK = 3


def test_structured_artifact_summary_handles_pytest_coverage(tmp_path: Path) -> None:
    """Pytest artifacts summarize test failures and coverage gaps."""

    junit = tmp_path / "pytest-junit.xml"
    junit.write_text(
        """<?xml version="1.0"?>
<testsuites>
  <testsuite tests="2" failures="1" errors="0" skipped="0">
    <testcase classname="tests.test_example" name="test_failure">
      <failure message="assert 1 == 2">AssertionError</failure>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        """
{
  "totals": {
    "covered_lines": 8,
    "num_statements": 10,
    "missing_lines": 2,
    "percent_covered_display": "80"
  },
  "files": {
    "src/example.py": {
      "summary": {"percent_covered_display": "50"},
      "missing_lines": [3, 4]
    }
  }
}
""",
        encoding="utf-8",
    )

    summary = maintainer_reporting.structured_artifact_summary(
        "pytest-coverage",
        (str(junit), str(coverage)),
    )

    assert summary is not None
    assert "pytest: 2 tests, 1 failures, 0 errors, 0 skipped" in summary
    assert "tests.test_example::test_failure: failure: assert 1 == 2" in summary
    assert "coverage total: 80% (8/10 lines, 2 missing)" in summary
    assert "src/example.py: 50%, 2 missing (3, 4)" in summary


def test_structured_artifact_summary_handles_java_reports(tmp_path: Path) -> None:
    """Java artifacts summarize debt and test totals without raw XML."""
    artifact = tmp_path / "java-gradle-static.json"
    artifact.write_text(
        json.dumps(
            {
                "provider": "java-gradle",
                "reports": {
                    "finding_count": 3,
                    "baseline": {
                        "new_occurrences": 1,
                        "metric_regressions": [{"current": 12, "ceiling": 10}],
                    },
                    "tests": {
                        "tests": 5,
                        "failures": 1,
                        "errors": 0,
                        "skipped": 2,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    summary = maintainer_reporting.structured_artifact_summary(
        "java-gradle-static",
        (str(artifact),),
    )

    assert summary == (
        "java findings: 3 reported, 1 new, 1 metric regressions\n"
        "java tests: 5 run, 1 failures, 0 errors, 2 skipped"
    )


def test_structured_artifact_summary_handles_security_json_artifacts(
    tmp_path: Path,
) -> None:
    """Security artifacts summarize findings without leaking secret values."""

    semgrep = tmp_path / "semgrep.json"
    semgrep.write_text(
        """
{
  "results": [
    {
      "check_id": "python.subprocess.shell-true",
      "path": "src/example.py",
      "start": {"line": 4, "col": 8},
      "extra": {"severity": "ERROR", "message": "shell=True"}
    }
  ]
}
""",
        encoding="utf-8",
    )
    osv = tmp_path / "osv-scanner.json"
    osv.write_text(
        """
{
  "results": [
    {
      "source": {"path": "package-lock.json", "type": "lockfile"},
      "packages": [
        {
          "package": {"ecosystem": "PyPI", "name": "demo", "version": "1.0"},
          "vulnerabilities": [{"id": "PYSEC-1", "summary": "demo vuln"}]
        }
      ]
    }
  ]
}
""",
        encoding="utf-8",
    )
    secret_scan = tmp_path / "secret-scan-ci.json"
    secret_scan.write_text(
        """
[
  {
    "RuleID": "generic-api-key",
    "Description": "Generic API key",
    "File": "src/example.py",
    "StartLine": 5,
    "StartColumn": 9,
    "Secret": "do-not-print"
  }
]
""",
        encoding="utf-8",
    )
    pip_audit = tmp_path / "pip-audit.json"
    pip_audit.write_text(
        """
{
  "dependencies": [
    {
      "name": "demo",
      "version": "1.0",
      "vulns": [{"id": "PYSEC-2", "fix_versions": ["1.1"]}]
    }
  ]
}
""",
        encoding="utf-8",
    )

    semgrep_summary = maintainer_reporting.structured_artifact_summary(
        "semgrep",
        (str(semgrep),),
    )
    osv_summary = maintainer_reporting.structured_artifact_summary(
        "osv-scanner",
        (str(osv),),
    )
    secret_summary = maintainer_reporting.structured_artifact_summary(
        "secret-scan",
        (str(secret_scan),),
    )
    pip_audit_summary = maintainer_reporting.structured_artifact_summary(
        "pip-audit",
        (str(pip_audit),),
    )

    assert semgrep_summary == ("src/example.py:4:8: python.subprocess.shell-true ERROR: shell=True")
    assert osv_summary == ("PyPI/demo 1.0: PYSEC-1; source: package-lock.json; demo vuln")
    assert secret_summary == "src/example.py:5:9: generic-api-key: Generic API key"
    assert "do-not-print" not in secret_summary
    assert pip_audit_summary == "demo 1.0: PYSEC-2 fix: 1.1"


def test_structured_artifact_summary_handles_missing_and_bad_artifacts(
    tmp_path: Path,
) -> None:
    """Malformed structured artifacts fall back to raw-output summaries."""

    missing = tmp_path / "missing.json"
    bad_json = tmp_path / "semgrep.json"
    bad_json.write_text("{not-json", encoding="utf-8")
    bad_xml = tmp_path / "pytest-junit.xml"
    bad_xml.write_text("<testsuites>", encoding="utf-8")
    bad_coverage = tmp_path / "coverage.json"
    bad_coverage.write_text("{not-json", encoding="utf-8")

    assert (
        structured_artifacts.summarize_json_artifact(
            (str(missing),),
            "missing.json",
            lambda _payload: "unused",
        )
        is None
    )
    assert (
        structured_artifacts.summarize_json_artifact(
            (str(bad_json),),
            "semgrep.json",
            lambda _payload: "unused",
        )
        is None
    )
    assert structured_pytest.summarize_junit_artifact((str(missing),)) is None
    assert structured_pytest.summarize_junit_artifact((str(bad_xml),)) is None
    assert structured_pytest.summarize_coverage_artifact((str(missing),)) is None
    assert structured_pytest.summarize_coverage_artifact((str(bad_coverage),)) is None
    assert structured_pytest.summarize_coverage_payload([]) is None
    assert structured_pytest.summarize_coverage_payload({"totals": [], "files": {}}) is None
    assert structured_security.summarize_semgrep_payload([]) is None
    assert structured_security.summarize_semgrep_payload({"results": {}}) is None
    assert structured_security.summarize_osv_payload([]) is None
    assert structured_security.summarize_pip_audit_payload([]) is None
    assert structured_security.summarize_pip_audit_payload({"dependencies": {}}) is None


def test_pytest_summary_caps_failures_and_missing_coverage(
    tmp_path: Path,
) -> None:
    """Pytest summaries report omitted failures and worst coverage files."""

    cases = "\n".join(
        (
            f'<testcase classname="tests.test_example" name="test_{index}">'
            f'<failure message="failure {index}">trace</failure>'
            "</testcase>"
        )
        for index in range(structured_pytest.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
    )
    junit = tmp_path / "pytest-junit.xml"
    junit.write_text(
        f"""<?xml version="1.0"?>
<testsuite tests="51" failures="51" errors="0" skipped="0">
{cases}
</testsuite>
""",
        encoding="utf-8",
    )
    coverage_files: dict[str, object] = {
        f"src/example_{index}.py": {
            "summary": {"percent_covered": 12.345},
            "missing_lines": list(range(1, 12)),
        }
        for index in range(structured_pytest.COVERAGE_FILE_PREVIEW + 1)
    }
    coverage_files["src/ignored.py"] = []
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        (
            '{"totals":{"covered_lines":"1","num_statements":"2",'
            '"missing_lines":"1","percent_covered":50.0},'
            f'"files":{json.dumps(coverage_files)}}}'
        ),
        encoding="utf-8",
    )

    summary = maintainer_reporting.structured_artifact_summary(
        "pytest-coverage",
        (str(junit), str(coverage)),
    )

    assert summary is not None
    assert "1 more pytest failures omitted" in summary
    assert "1 more files with missing coverage omitted" in summary
    assert "1, 2, 3, 4, 5, 6, 7, 8, ..." in summary
    assert structured_pytest.percent_value({}) == "?%"
    assert structured_pytest.int_value("bad", default=PYTEST_INT_FALLBACK) == PYTEST_INT_FALLBACK


def test_security_summaries_cap_and_ignore_invalid_payloads() -> None:
    """Security summaries cap long outputs and ignore malformed nested data."""

    semgrep_payload: dict[str, object] = {
        "results": [
            {
                "check_id": f"rule-{index}",
                "path": "src/example.py",
                "start": {"line": "bad", "col": "bad"},
                "extra": {},
            }
            for index in range(structured_security.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
        ]
    }
    gitleaks_payload: list[object] = [
        {"RuleID": f"rule-{index}", "File": "src/example.py"}
        for index in range(structured_security.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
    ]
    pip_audit_payload: dict[str, object] = {
        "dependencies": [
            {"name": "bad", "vulns": {}},
            {
                "name": "demo",
                "version": "1.0",
                "vulns": [
                    {"id": f"PYSEC-{index}"}
                    for index in range(structured_security.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
                ],
            },
        ]
    }
    osv_payload: dict[str, object] = {
        "results": [
            {"packages": {}},
            {
                "packages": [
                    {"package": "bad", "vulnerabilities": {}},
                    {
                        "package": {"name": "demo", "version": "1.0"},
                        "vulnerabilities": [
                            {"id": f"OSV-{index}"}
                            for index in range(structured_security.STRUCTURED_DIAGNOSTIC_LIMIT + 1)
                        ],
                    },
                ]
            },
        ]
    }

    assert "1 more Semgrep findings omitted" in (
        structured_security.summarize_semgrep_payload(semgrep_payload) or ""
    )
    assert "1 more secret-scan findings omitted" in (
        structured_security.summarize_gitleaks_payload(gitleaks_payload) or ""
    )
    assert "1 more pip-audit findings omitted" in (
        structured_security.summarize_pip_audit_payload(pip_audit_payload) or ""
    )
    assert "2 more OSV vulnerabilities omitted" in (
        structured_security.summarize_osv_payload(osv_payload) or ""
    )
    assert structured_security.format_gitleaks_finding({}) == ("<unknown>:1:1: gitleaks:")
    assert (
        structured_security.int_value("bad", default=SECURITY_INT_FALLBACK) == SECURITY_INT_FALLBACK
    )
    assert structured_security.str_value(None, default="fallback") == "fallback"
