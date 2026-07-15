"""Tests for aggregate-only verifier CLI mode."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.verify import partial_runs
from agent_maintainer.verify import quiet as verify_quiet


def test_main_aggregate_only_writes_manifest_without_loading_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Aggregate-only mode combines uploaded partials without running checks."""

    output = tmp_path / "combined.json"

    def fail_load_config() -> MaintainerConfig:
        pytest.fail("aggregate-only mode must not load verifier configuration")

    monkeypatch.setattr(verify_quiet.core_config, "load_config", fail_load_config)

    def fake_aggregate(paths: Sequence[Path]) -> dict[str, object]:
        return {"version": 1, "paths": [str(path) for path in paths]}

    monkeypatch.setattr(
        partial_runs.verification_aggregate,
        "aggregate_partial_manifests",
        fake_aggregate,
    )

    status = verify_quiet.main(
        [
            "--aggregate-partial",
            "tests.json",
            "--aggregate-partial",
            "static.json",
            "--aggregate-output",
            str(output),
        ]
    )

    assert status == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "paths": ["tests.json", "static.json"],
        "version": 1,
    }
    assert "PASS: aggregated 2 verifier groups" in capsys.readouterr().out
