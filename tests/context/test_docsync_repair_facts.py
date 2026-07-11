"""Tests DocSync exact repair fact extraction."""

from __future__ import annotations

import json
from pathlib import Path

from agent_context.failures import FailureRecord
from agent_context.next_actions import next_action_commands
from agent_maintainer.context.pack import exact_facts


def test_docsync_json_report_extracts_exact_repair_fact(tmp_path: Path) -> None:
    """DocSync report locations become context-pack repair facts."""

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "DS201",
                        "severity": "error",
                        "message": "Evidence changed without reviewed docs.",
                        "locations": [
                            {
                                "path": "src/demo.py",
                                "start_line": 12,
                                "end_line": 18,
                                "inclusive": True,
                            }
                        ],
                        "related_claims": ["claim.demo"],
                        "related_evidence": ["evidence.demo"],
                    }
                ],
                "ok": False,
            },
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(
        tmp_path,
        (record("docsync", report_path),),
    )

    assert facts == [
        {
            "check": "docsync",
            "path": "src/demo.py",
            "line": 12,
            "column": None,
            "symbol": "DS201",
            "message": "Evidence changed without reviewed docs.",
            "severity": "error",
        }
    ]
    assert next_action_commands(facts, ())[:1] == [
        "python -m agent_maintainer context file src/demo.py --around 12 --context 30"
    ]


def test_docsync_json_report_without_locations_keeps_check_fact(
    tmp_path: Path,
) -> None:
    """DocSync findings without locations still produce actionable check facts."""

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "code": "DS000",
                        "severity": "error",
                        "message": "Unable to inspect Git diff.",
                        "locations": [],
                    }
                ],
                "ok": False,
            },
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("docsync", report_path),))

    assert facts == [
        {
            "check": "docsync",
            "path": None,
            "line": None,
            "column": None,
            "symbol": "DS000",
            "message": "Unable to inspect Git diff.",
            "severity": "error",
        }
    ]


def test_docsync_json_report_skips_non_object_findings(tmp_path: Path) -> None:
    """Malformed finding entries cannot obscure a valid repair fact."""

    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    None,
                    {
                        "code": "DS201",
                        "severity": "error",
                        "message": "Evidence changed without reviewed docs.",
                        "locations": [{"path": "src/demo.py", "start_line": 12}],
                    },
                ],
                "ok": False,
            },
        ),
        encoding="utf-8",
    )

    facts = exact_facts.repair_facts(tmp_path, (record("docsync", report_path),))

    assert len(facts) == 1
    assert facts[0]["symbol"] == "DS201"


def record(check: str, artifact_path: Path) -> FailureRecord:
    """Build failed check record with a structured artifact."""

    return FailureRecord(
        name=check,
        status="failed",
        category="docs",
        priority=1,
        exit_code=1,
        log_path=str(artifact_path.with_suffix(".log")),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(artifact_path),),
    )
