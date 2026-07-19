"""Tests generated configuration reference and capability metadata."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from agent_maintainer.config import reference, registry
from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.core.structured_values import json_array, json_object
from tests.support.paths import REPO_ROOT

CPP_REFERENCE_APPENDIX = """## C/C++ (CMake) Provider

The experimental provider is disabled by default. Phase 187 accepts the nested
configuration below for classification, advisory suppression evidence, and
static doctor only. Configured commands are not executed. Typed report
declarations are unavailable until Phase 188.

```toml
[tool.agent_maintainer.cpp]
```

| Nested key | Type | Default |
|---|---|---|
| `enabled` | bool | `false` |
| `cmake_root` | str | `"."` |
| `format_command` | command array | `[]` |
| `static_analysis_command` | command array | `[]` |
| `build_command` | command array | `[]` |
| `test_command` | command array | `[]` |
| `coverage_command` | command array | `[]` |
| `format_profiles` | profile array | `["precommit","full","ci"]` |
| `static_analysis_profiles` | profile array | `["precommit","full","ci"]` |
| `build_profiles` | profile array | `["full","ci"]` |
| `test_profiles` | profile array | `["full","ci"]` |
| `coverage_profiles` | profile array | `["full","ci"]` |
"""


def test_generated_reference_is_current() -> None:
    """Checked-in human and machine references cannot drift from the registry."""
    checked_in = (REPO_ROOT / reference.REFERENCE_PATH).read_text(encoding="utf-8")
    generated_core = reference.render_reference_markdown()

    assert checked_in == f"{generated_core}\n{CPP_REFERENCE_APPENDIX}"
    assert (REPO_ROOT / reference.CAPABILITIES_PATH).read_text(
        encoding="utf-8"
    ) == reference.render_capabilities_json()


def test_payload_covers_fields_and_tables() -> None:
    """Machine metadata covers every field and supported nested table."""

    payload = reference.capability_payload()
    fields = json_array(payload["fields"])
    nested = json_object(payload["nested_tables"])

    assert fields is not None
    names = {
        name
        for item in fields
        if (row := json_object(item)) is not None
        if isinstance(name := row.get("name"), str)
    }
    assert names == set(registry.FIELD_SPECS)
    assert nested is not None
    assert set(nested) == {
        "diagnostics",
        "file_baselines",
        "file_baselines.groups.*",
        "java",
        "java.reports.*",
        "workspaces.*",
    }
    assert payload["nested_environment"] == {"java.enabled": "AGENT_MAINTAINER_JAVA_ENABLED"}


def test_reference_cli_writes_and_detects_drift(tmp_path: Path) -> None:
    """The generator supports reproducible write and currentness workflows."""

    assert reference.main(["--root", str(tmp_path)]) == reference.SUCCESS_STATUS
    assert reference.outdated_generated(tmp_path) == ()
    capability_path = tmp_path / reference.CAPABILITIES_PATH
    capability_path.write_text("{}\n", encoding="utf-8")

    assert reference.main(["--root", str(tmp_path), "--check"]) == reference.DRIFT_STATUS


def test_capability_json_is_stable() -> None:
    """Machine capability output is stable JSON with an explicit schema version."""

    rendered = reference.render_capabilities_json()
    payload = json.loads(rendered)

    assert rendered == reference.render_capabilities_json()
    assert (REPO_ROOT / reference.CAPABILITIES_PATH).read_text(encoding="utf-8") == rendered
    assert payload["schema_version"] == reference.CAPABILITY_SCHEMA_VERSION


def test_human_reference_exposes_nested_environment_override() -> None:
    rendered = reference.render_reference_markdown()

    assert "## Nested Environment Overrides" in rendered
    assert "| `java.enabled` | `AGENT_MAINTAINER_JAVA_ENABLED` |" in rendered


def test_human_reference_documents_cpp_cmake_configuration() -> None:
    """The public reference names the complete nested C/C++ configuration."""
    rendered = Path("docs/configuration-reference.md").read_text(encoding="utf-8")

    assert "## C/C++ (CMake) Provider" in rendered
    assert "[tool.agent_maintainer.cpp]" in rendered
    for field in fields(CppCmakeConfig):
        assert field.name in rendered
    for expected_row in (
        "| `enabled` | bool | `false` |",
        '| `cmake_root` | str | `"."` |',
        "| `format_command` | command array | `[]` |",
        "| `static_analysis_command` | command array | `[]` |",
        "| `build_command` | command array | `[]` |",
        "| `test_command` | command array | `[]` |",
        "| `coverage_command` | command array | `[]` |",
        '| `format_profiles` | profile array | `["precommit","full","ci"]` |',
        '| `static_analysis_profiles` | profile array | `["precommit","full","ci"]` |',
        '| `build_profiles` | profile array | `["full","ci"]` |',
        '| `test_profiles` | profile array | `["full","ci"]` |',
        '| `coverage_profiles` | profile array | `["full","ci"]` |',
    ):
        assert expected_row in rendered


def test_human_reference_documents_explicit_java_baseline_lifecycle() -> None:
    """The generated reference gives operators the safe lifecycle commands."""
    rendered = reference.render_reference_markdown()

    assert "assess java-baseline create" in rendered
    assert "assess java-baseline inspect" in rendered
    assert "assess java-baseline prune" in rendered
    assert "never changes the baseline during verification" in rendered
    assert "assess file-baselines create" in rendered
    assert "assess file-baselines inspect" in rendered
    assert "assess file-baselines prune" in rendered
    assert "Renamed paths never inherit" in rendered
