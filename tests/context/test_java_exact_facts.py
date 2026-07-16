"""Tests exact repair facts from bounded Java Gradle artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import pytest

from agent_context.failures import FailureRecord
from agent_context.reading import file_safety
from agent_maintainer.context.pack import exact_facts
from agent_repair_facts import registry
from agent_repair_facts.parsers import java

ENCODING = "utf-8"
CHECK = "java-gradle-static"
FINDING_LINE = 9


def test_registry_discovers_java_findings_and_test_problems(tmp_path: Path) -> None:
    """Both Java check groups dispatch their bounded artifact facts."""
    payload = java_payload()
    static_facts = registry.artifact_facts_from_text(
        CHECK,
        tmp_path / "java-gradle-static.json",
        json.dumps(payload),
    )
    test_facts = registry.artifact_facts_from_text(
        "java-gradle-tests",
        tmp_path / "java-gradle-tests.json",
        json.dumps(payload),
    )

    assert static_facts[0]["symbol"] == "example.ApiTest#loads"
    assert static_facts[1]["path"] == "src/main/java/example/App.java"
    assert static_facts[1]["line"] == FINDING_LINE
    assert [fact["symbol"] for fact in test_facts] == [fact["symbol"] for fact in static_facts]
    assert test_facts[0]["check"] == "java-gradle-tests"


def test_context_pipeline_reads_java_artifact_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Java parsing consumes the single confined bounded read from context."""
    artifact = write_payload(tmp_path / "java-gradle-static.json", java_payload())
    original_open = file_safety.os.open
    open_flags: list[int] = []

    def tracked_open(path: Path, flags: int) -> int:
        if Path(path) == artifact:
            open_flags.append(flags)
        return original_open(path, flags)

    def forbidden_reopen(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("Java parser reopened an already captured artifact")

    monkeypatch.setattr(file_safety.os, "open", tracked_open)
    monkeypatch.setattr(Path, "read_text", forbidden_reopen)

    facts = exact_facts.repair_facts(tmp_path, (failure(artifact),))

    assert facts[0]["symbol"] == "example.ApiTest#loads"
    assert len(open_flags) == 1
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    assert no_follow == 0 or open_flags[0] & no_follow


def test_unsafe_embedded_and_manifest_paths_do_not_escape_workspace(tmp_path: Path) -> None:
    """Neither artifact metadata nor manifest paths can target outside files."""
    payload = java_payload()
    reports = cast(dict[str, object], payload["reports"])
    findings = cast(list[object], reports["findings"])
    finding = cast(dict[str, object], findings[0])
    finding["path"] = "../../etc/passwd"
    artifact = write_payload(tmp_path / "java-gradle-static.json", payload)

    parsed = registry.artifact_facts_from_text(CHECK, artifact, json.dumps(payload))
    escaped = exact_facts.repair_facts(
        tmp_path,
        (
            FailureRecord(
                name=CHECK,
                status="failed",
                category="test",
                priority=1,
                exit_code=1,
                log_path="java.log",
                log_bytes=0,
                expansion_commands=(),
                artifact_paths=("../java-gradle-static.json",),
            ),
        ),
        workspace_root=tmp_path,
        require_relative_paths=True,
    )

    assert parsed[1]["path"] is None
    assert escaped[0]["message"] == f"{CHECK} failed with exit code 1"


def test_java_parser_caps_facts_and_rejects_malformed_artifacts(tmp_path: Path) -> None:
    """Large or malformed payloads stay concise and fail closed."""
    payload = java_payload()
    reports = cast(dict[str, object], payload["reports"])
    finding = cast(list[object], reports["findings"])
    reports["findings"] = finding * (java.MAX_JAVA_FACTS + 2)

    facts = registry.artifact_facts_from_text(CHECK, tmp_path / "java.json", json.dumps(payload))

    assert len(facts) == java.MAX_JAVA_FACTS
    assert registry.artifact_facts_from_text(CHECK, tmp_path / "bad.json", "{") == []
    assert (
        registry.artifact_facts_from_text(
            CHECK,
            tmp_path / "wrong.json",
            '{"provider":"other","reports":{}}',
        )
        == []
    )


def java_payload() -> dict[str, object]:
    """Return one runner-compatible sanitized Java artifact."""
    return {
        "schema_version": 1,
        "provider": "java-gradle",
        "group": "static",
        "status": "report-failed",
        "reports": {
            "finding_count": 1,
            "findings": [
                {
                    "tool": "checkstyle",
                    "rule": "Naming",
                    "path": "src/main/java/example/App.java",
                    "subject": "Naming",
                    "message": "Name must match",
                    "severity": "error",
                    "line": FINDING_LINE,
                    "metric": None,
                    "fingerprint": "a" * 64,
                },
            ],
            "findings_truncated": False,
            "tests": {
                "tests": 2,
                "failures": 0,
                "errors": 1,
                "skipped": 0,
                "problems": [
                    {
                        "suite": "api",
                        "testcase": "example.ApiTest#loads",
                        "kind": "error",
                        "message": "boom",
                        "details": "error trace",
                    },
                ],
                "problems_truncated": False,
            },
            "baseline": {
                "present": True,
                "passed": False,
                "new_occurrences": 1,
                "metric_regressions": [],
            },
        },
    }


def write_payload(path: Path, payload: dict[str, object]) -> Path:
    """Write one Java artifact fixture."""
    path.write_text(json.dumps(payload), encoding=ENCODING)
    return path


def failure(artifact: Path) -> FailureRecord:
    """Return one failed Java check referencing the artifact."""
    return FailureRecord(
        name=CHECK,
        status="failed",
        category="test",
        priority=1,
        exit_code=1,
        log_path=str(artifact.with_suffix(".log")),
        log_bytes=0,
        expansion_commands=(),
        artifact_paths=(str(artifact),),
    )
