"""Tests for the canonical run-artifact package boundary."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

FACADE_MODULES = (
    "artifact_manifest",
    "git_state",
    "history",
    "pr_summary",
    "pr_summary_support",
    "timing",
)
CANONICAL_PACKAGE = "agent_run_artifacts"
OLD_PACKAGE = "agent_maintainer.verify"


def test_run_artifact_compatibility_facades_are_removed() -> None:
    """Extracted artifact helpers have one import owner, not forwarding paths."""

    for module_name in FACADE_MODULES:
        assert find_spec(f"{OLD_PACKAGE}.{module_name}") is None
        assert find_spec(f"{CANONICAL_PACKAGE}.{module_name}") is not None


def test_verify_architecture_contract_omits_removed_facades() -> None:
    """The verify domain contract must not retain deleted module entries."""

    contract = Path("src/agent_maintainer/verify/tach.domain.toml").read_text(
        encoding="utf-8",
    )
    for module_name in FACADE_MODULES:
        assert f'path = "{module_name}"' not in contract


def test_compatibility_inventory_omits_removed_facade_group() -> None:
    """The public inventory lists only compatibility modules that still exist."""

    inventory = Path("docs/compatibility-shims.md").read_text(encoding="utf-8")
    assert "Run-artifact extraction" not in inventory
    assert "`agent_maintainer.verify.artifact_manifest`" not in inventory
