"""Tests Java/Gradle catalog integration."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig


def test_java_checks_are_absent_by_default() -> None:
    checks = maintainer_catalog.make_checks(MaintainerConfig(), "HEAD", "origin/main")

    assert not [check for check in checks if check.name.startswith("java-gradle-")]


def test_enabled_java_checks_follow_typescript_and_precede_workflow_checks() -> None:
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotless", "spotbugs", "test"),
            spotless_tasks=("spotlessCheck",),
            spotbugs_tasks=("spotbugsMain",),
            test_tasks=("test",),
        ),
    )

    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main")
    names = [check.name for check in checks]

    assert names[names.index("typescript-dependency-cruiser") + 1 : names.index("actionlint")] == [
        "java-gradle-format",
        "java-gradle-static",
        "java-gradle-tests",
    ]
