"""Public rendering API for bundled Java/Gradle templates."""

from __future__ import annotations

import re
from importlib import resources

from agent_maintainer.ecosystems.java.defaults import JAVA_DEFAULTS, JAVA_TOOL_VERSIONS

_VERSION_REPLACEMENTS = (
    ("@SPOTLESS_PLUGIN_VERSION@", JAVA_TOOL_VERSIONS.spotless_plugin),
    ("@SPOTBUGS_PLUGIN_VERSION@", JAVA_TOOL_VERSIONS.spotbugs_plugin),
    ("@CHECKSTYLE_VERSION@", JAVA_TOOL_VERSIONS.checkstyle),
    ("@PMD_VERSION@", JAVA_TOOL_VERSIONS.pmd),
    ("@JACOCO_VERSION@", JAVA_TOOL_VERSIONS.jacoco),
    ("@GOOGLE_JAVA_FORMAT_VERSION@", JAVA_TOOL_VERSIONS.google_java_format),
)
_POLICY_REPLACEMENTS = (
    ("@CYCLOMATIC_COMPLEXITY@", str(JAVA_DEFAULTS.cyclomatic_complexity)),
    ("@COGNITIVE_COMPLEXITY@", str(JAVA_DEFAULTS.cognitive_complexity)),
    ("@NPATH_COMPLEXITY@", str(JAVA_DEFAULTS.npath_complexity)),
    ("@MAX_PHYSICAL_LINES@", str(JAVA_DEFAULTS.max_physical_lines)),
)
SAFE_CI_VALUE = re.compile(r"[A-Za-z0-9._/-]+")
SAFE_GRADLE_TASK = re.compile(r":?[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)*")


def _replace_tokens(text: str, replacements: tuple[tuple[str, str], ...]) -> str:
    rendered = text
    for token, value in replacements:
        rendered = rendered.replace(token, value)
    return rendered


def _template_text(filename: str) -> str:
    template = resources.files(__package__).joinpath(filename)
    return template.read_text(encoding="utf-8")


def ruleset_text(name: str) -> str:
    """Render one curated non-format Java ruleset."""

    filenames = (("checkstyle", "checkstyle.xml"), ("pmd", "pmd.xml"))
    filename = next((path for choice, path in filenames if choice == name), None)
    if filename is None:
        raise ValueError(f"unsupported Java ruleset: {name}")
    return _replace_tokens(_template_text(filename), _POLICY_REPLACEMENTS)


def render_build_fragment(dsl: str) -> str:
    """Render one pinned Groovy or Kotlin DSL setup fragment."""

    filenames = (("groovy", "build.gradle"), ("kotlin", "build.gradle.kts"))
    filename = next((name for choice, name in filenames if choice == dsl), None)
    if filename is None:
        raise ValueError(f"unsupported Gradle DSL: {dsl}")
    return _replace_tokens(_template_text(filename), _VERSION_REPLACEMENTS)


def render_ci_workflow(
    *,
    jdk_distribution: str,
    jdk_version: str,
    static_tasks: tuple[str, ...],
    test_tasks: tuple[str, ...],
    spotless_ratchet_ref: str = "",
) -> str:
    """Render the dedicated two-job GitHub Actions workflow."""
    _validate_ci_value(jdk_distribution, "JDK distribution")
    _validate_ci_value(jdk_version, "JDK version")
    if not static_tasks or not test_tasks:
        raise ValueError("Java CI requires explicit static and test task groups")
    if any(SAFE_GRADLE_TASK.fullmatch(task) is None for task in (*static_tasks, *test_tasks)):
        raise ValueError("Java CI contains an unsafe Gradle task")
    if spotless_ratchet_ref:
        _validate_ci_value(spotless_ratchet_ref, "Spotless ratchet reference")
    return _ci_workflow_text(
        jdk_distribution,
        jdk_version,
        static_tasks,
        test_tasks,
        spotless_ratchet_ref,
    )


def _validate_ci_value(value: str, label: str) -> None:
    if SAFE_CI_VALUE.fullmatch(value) is None or ".." in value:
        raise ValueError(f"{label} contains unsupported characters")


def _ci_workflow_text(
    distribution: str,
    version: str,
    static_tasks: tuple[str, ...],
    test_tasks: tuple[str, ...],
    ratchet_ref: str,
) -> str:
    checkout_options = "\n        with:\n          fetch-depth: 0" if ratchet_ref else ""
    ratchet_step = (
        "\n      - name: Verify Spotless ratchet reference\n"
        f"        run: git rev-parse --verify --end-of-options '{ratchet_ref}^{{commit}}'"
        if ratchet_ref
        else ""
    )
    static_command = " ".join(("./gradlew", "--console=plain", "--continue", *static_tasks))
    test_command = " ".join(("./gradlew", "--console=plain", "--continue", *test_tasks))
    job_template = """      - uses: actions/checkout@v4{checkout_options}
      - uses: actions/setup-java@v4
        with:
          distribution: {distribution}
          java-version: '{version}'
          cache: gradle
      - uses: gradle/actions/setup-gradle@v4{ratchet_step}
      - run: {command}
"""
    static_steps = job_template.format(
        checkout_options=checkout_options,
        distribution=distribution,
        version=version,
        ratchet_step=ratchet_step,
        command=static_command,
    )
    test_steps = job_template.format(
        checkout_options="",
        distribution=distribution,
        version=version,
        ratchet_step="",
        command=test_command,
    )
    return f"""name: Agent Maintainer Java

on:
  pull_request:
  push:

jobs:
  static-and-policy:
    runs-on: ubuntu-latest
    steps:
{static_steps}  tests-and-coverage:
    runs-on: ubuntu-latest
    steps:
{test_steps}"""
