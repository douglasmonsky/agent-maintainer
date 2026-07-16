"""Public rendering API for bundled Java/Gradle templates."""

from __future__ import annotations

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
