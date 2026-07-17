"""Tests Java/Gradle setup advisor recommendations."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.assess.setup_advisor import build_setup_report

COMPLETE_PARTS = ("wrapper", "build", "source")
PROVIDER_NAME = "java-gradle-provider"
TEXT_ENCODING = "utf-8"


def test_complete_java_repo_enables_provider(tmp_path: Path) -> None:
    """Complete concrete evidence enables the Java provider recommendation."""
    write_java_gradle_repo(tmp_path, COMPLETE_PARTS)

    report = build_setup_report(collect_evidence(tmp_path))
    gates = {gate.name: gate for gate in report.optional_gates}

    assert report.track == "core"
    assert report.preset == "strict-new-repo"
    assert gates[PROVIDER_NAME].recommendation == "enable"
    assert gates[PROVIDER_NAME].config_key == "enable_java"


def test_java_gate_explains_concrete_evidence(tmp_path: Path) -> None:
    """Java advice explains the wrapper, build, and source facts supporting it."""
    write_java_gradle_repo(tmp_path, COMPLETE_PARTS)

    report = build_setup_report(collect_evidence(tmp_path))
    gate = next(gate for gate in report.optional_gates if gate.name == PROVIDER_NAME)

    assert "Gradle wrapper" in gate.reason
    assert "build.gradle.kts" in gate.reason
    assert "Java source" in gate.reason
    assert any("reviewed Java Gradle setup plan" in prompt for prompt in report.agent_prompts)


@pytest.mark.parametrize("missing", COMPLETE_PARTS)
def test_partial_java_repo_stays_inspect(tmp_path: Path, missing: str) -> None:
    """Partial Java-looking evidence cannot authorize Java setup."""
    parts = tuple(part for part in COMPLETE_PARTS if part != missing)
    write_java_gradle_repo(tmp_path, parts)

    report = build_setup_report(collect_evidence(tmp_path))
    gate_names = {gate.name for gate in report.optional_gates}

    assert report.track == "inspect"
    assert PROVIDER_NAME not in gate_names


def write_java_gradle_repo(root: Path, parts: tuple[str, ...]) -> None:
    """Write only the requested concrete Java/Gradle evidence parts."""
    if "wrapper" in parts:
        (root / "gradlew").write_text("#!/bin/sh\n", encoding=TEXT_ENCODING)
    if "build" in parts:
        (root / "build.gradle.kts").write_text("plugins { java }\n", encoding=TEXT_ENCODING)
    if "source" in parts:
        source = root / "src" / "main" / "java" / "example" / "App.java"
        source.parent.mkdir(parents=True)
        source.write_text("package example;\nclass App {}\n", encoding=TEXT_ENCODING)
