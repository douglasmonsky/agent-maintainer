"""Tests conservative Java/Gradle repository path classification."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.java.classification import classify_path
from agent_maintainer.ecosystems.models import FileRole
from agent_maintainer.ecosystems.registry import classification_candidates

JAVA_CONFIG = MaintainerConfig(java=JavaGradleConfig(enabled=True))


@pytest.mark.parametrize(
    ("path", "role", "generated", "ignored"),
    [
        ("src/main/java/com/acme/App.java", FileRole.SOURCE, False, False),
        ("module/src/main/java/com/acme/App.java", FileRole.SOURCE, False, False),
        ("src/test/java/com/acme/AppTest.java", FileRole.TEST, False, False),
        ("build.gradle", FileRole.CONFIG, False, False),
        ("build.gradle.kts", FileRole.CONFIG, False, False),
        ("settings.gradle", FileRole.CONFIG, False, False),
        ("settings.gradle.kts", FileRole.CONFIG, False, False),
        ("gradle.properties", FileRole.CONFIG, False, False),
        ("gradle/libs.versions.toml", FileRole.CONFIG, False, False),
        ("backend/gradle/libs.versions.toml", FileRole.CONFIG, False, False),
        ("config/checkstyle/checkstyle.xml", FileRole.CONFIG, False, False),
        ("config/pmd/ruleset.xml", FileRole.CONFIG, False, False),
        ("gradlew", FileRole.DEPENDENCY, False, False),
        ("gradlew.bat", FileRole.DEPENDENCY, False, False),
        ("gradle/wrapper/gradle-wrapper.jar", FileRole.DEPENDENCY, False, False),
        ("gradle/wrapper/gradle-wrapper.properties", FileRole.DEPENDENCY, False, False),
        ("backend/gradle/wrapper/gradle-wrapper.properties", FileRole.DEPENDENCY, False, False),
        ("gradle.lockfile", FileRole.DEPENDENCY, False, False),
        ("build/generated/sources/Foo.java", FileRole.GENERATED, True, True),
        (".gradle/caches/state.bin", FileRole.IGNORED, False, True),
        ("scratch/Example.java", FileRole.UNKNOWN, False, False),
    ],
)
def test_java_path_roles(
    path: str,
    role: FileRole,
    generated: bool,
    ignored: bool,
) -> None:
    result = classify_path(path, JAVA_CONFIG.java)

    assert result.role == role
    assert result.generated is generated
    assert result.ignored is ignored


def test_java_classification_uses_configured_roots() -> None:
    java = replace(
        JAVA_CONFIG.java,
        source_roots=("backend/java",),
        test_roots=("backend/java-tests",),
    )

    assert classify_path("backend/java/App.java", java).role == FileRole.SOURCE
    assert classify_path("backend/java-tests/AppTest.java", java).role == FileRole.TEST
    assert classify_path("src/main/java/App.java", java).role == FileRole.UNKNOWN


def test_registry_dispatches_java_only_when_enabled() -> None:
    assert classification_candidates("src/main/java/App.java", MaintainerConfig()) == ()

    enabled = classification_candidates("src/main/java/App.java", JAVA_CONFIG)

    assert [(item.ecosystem, item.role) for item in enabled] == [("java", FileRole.SOURCE)]
