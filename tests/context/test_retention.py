"""Tests context pack retention configuration."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_maintainer.config import schema
from agent_maintainer.hooks import context as hook_context


def test_context_pack_retention_defaults_are_local_only() -> None:
    """Context packs default to written, local-only, source-bearing artifacts."""

    config = schema.MaintainerConfig()

    assert config.context_write_context_packs is True
    assert config.context_packs_local_only is True
    assert config.context_pack_contains_source is True


def test_hook_failure_context_respects_disabled_pack_writes(tmp_path: Path) -> None:
    """Hook failure context does not write packs when disabled by config."""

    result = subprocess.CompletedProcess(["verify"], 1, "verify failed", "")
    config = schema.MaintainerConfig(context_write_context_packs=False)

    output = hook_context.failure_context(tmp_path, result, config, limit=1_000)

    assert "verify failed" in output
    assert "Context pack writing disabled by config." in output
    assert not (tmp_path / ".verify-logs" / "context").exists()
