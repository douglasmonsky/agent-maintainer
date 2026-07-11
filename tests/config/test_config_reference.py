"""Tests generated configuration reference and capability metadata."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.config import reference, registry
from tests.support.paths import REPO_ROOT


def test_generated_reference_is_current() -> None:
    """Checked-in human and machine references cannot drift from the registry."""

    assert reference.outdated_generated(REPO_ROOT) == ()


def test_payload_covers_fields_and_tables() -> None:
    """Machine metadata covers every field and supported nested table."""

    payload = reference.capability_payload()
    fields = payload["fields"]
    nested = payload["nested_tables"]

    assert isinstance(fields, list)
    assert {row["name"] for row in fields if isinstance(row, dict)} == set(registry.FIELD_SPECS)
    assert isinstance(nested, dict)
    assert set(nested) == {
        "diagnostics",
        "file_baselines",
        "file_baselines.groups.*",
        "workspaces.*",
    }


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
    assert payload["schema_version"] == reference.CAPABILITY_SCHEMA_VERSION
