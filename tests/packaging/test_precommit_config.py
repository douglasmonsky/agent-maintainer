"""Contracts for the fast commit and complete pre-push verification path."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def local_hooks(config_path: Path) -> dict[str, dict[str, object]]:
    """Return local pre-commit hooks keyed by stable id."""

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    repository = next(item for item in payload["repos"] if item["repo"] == "local")
    return {hook["id"]: hook for hook in repository["hooks"]}


def assert_fast_commit_contract(hooks: dict[str, dict[str, object]]) -> None:
    """Assert the shared staged and pre-push safety contract."""

    fast = hooks["agent-maintainer-fast"]
    affected = hooks["agent-maintainer-affected-tests"]
    prepush = hooks["agent-maintainer-prepush"]
    fast_entry = cast(str, fast["entry"])
    affected_entry = cast(str, affected["entry"])
    prepush_entry = cast(str, prepush["entry"])

    assert "verify --profile fast --base-ref HEAD --staged" in fast_entry
    assert "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1" in fast_entry
    assert fast["stages"] == ["pre-commit"]
    assert "test-intel run-changed --base-ref HEAD --staged" in affected_entry
    assert affected["stages"] == ["pre-commit"]
    assert "python3 -m agent_maintainer.hooks.pre_push" in prepush_entry
    assert "AGENT_MAINTAINER_ALLOW_FOREGROUND_WAIT=1" in prepush_entry
    assert "--base-ref HEAD" not in prepush_entry
    assert prepush["stages"] == ["pre-push"]
    assert all(hook["pass_filenames"] is False for hook in hooks.values())


def test_repository_hooks_use_fast_commit_and_complete_prepush_gates() -> None:
    """The dogfood repository keeps expensive complete checks off commit latency."""

    assert_fast_commit_contract(local_hooks(REPO_ROOT / ".pre-commit-config.yaml"))


def test_generated_hooks_match_repository_safety_contract(tmp_path: Path) -> None:
    """New repositories receive the same fast and fail-closed hook path."""

    from agent_maintainer.core.scaffold.templates import PRE_COMMIT_CONFIG

    config_path = tmp_path / ".pre-commit-config.yaml"
    config_path.write_text(PRE_COMMIT_CONFIG, encoding="utf-8")

    assert_fast_commit_contract(local_hooks(config_path))
