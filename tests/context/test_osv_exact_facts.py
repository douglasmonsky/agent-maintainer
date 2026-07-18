"""Tests OSV Scanner exact facts in bounded context packs."""

from __future__ import annotations

import json
from pathlib import Path

from agent_context.failures import FailureRecord
from agent_maintainer.context.pack import exact_facts

EXPECTED_CONTEXT_FACTS = 5
INPUT_FINDINGS = 7


def test_osv_context_uses_existing_five_fact_limit(tmp_path: Path) -> None:
    """OSV artifacts retain the context pack's existing per-check bound."""

    artifact_path = tmp_path / "osv-scanner.json"
    artifact_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source": {
                            "path": "package-lock.json",
                            "type": "lockfile",
                        },
                        "packages": [
                            {
                                "package": {
                                    "ecosystem": "npm",
                                    "name": "demo",
                                    "version": "1",
                                },
                                "vulnerabilities": [
                                    {"id": f"OSV-{index:03d}"} for index in range(INPUT_FINDINGS)
                                ],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    record = FailureRecord(
        name="osv-scanner",
        status="failed",
        category="security/tooling",
        priority=9,
        exit_code=1,
        log_path=str(tmp_path / "osv-scanner.log"),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(artifact_path),),
    )

    facts = exact_facts.repair_facts(tmp_path, (record,))

    assert len(facts) == EXPECTED_CONTEXT_FACTS
    assert [fact["symbol"] for fact in facts] == [
        f"OSV-{index:03d}" for index in range(EXPECTED_CONTEXT_FACTS)
    ]
