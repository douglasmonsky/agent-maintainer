"""Contract compatibility catalog and captured-artifact integration tests."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer import models
from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.core import executor
from agent_maintainer.verify.groups import STATIC_AND_POLICY_GROUP, checks_for_group

OPTIONAL_REASON = (
    ".agent-maintainer/contracts.toml is absent; "
    "contract compatibility is not configured"
)


def _contract_check(*, staged: bool = False) -> models.Check:
    checks = make_checks(
        MaintainerConfig(),
        "HEAD",
        "origin/main",
        staged=staged,
    )
    return next(item for item in checks if item.name == "contract-compatibility")


def test_contract_check_is_optional_and_exact() -> None:
    """Configured repositories receive one complete JSON compatibility gate."""
    check = _contract_check()

    assert check.profiles == models.ALL_PROFILES
    assert check.required_paths == (".agent-maintainer/contracts.toml",)
    assert check.optional_skip_reason == OPTIONAL_REASON
    assert check.optional_skip_status == models.SKIP_STATUS_MISSING_OPTIONAL
    assert check.command == [
        sys.executable,
        "-m",
        "agent_maintainer",
        "contract",
        "check",
        "--base-ref",
        "HEAD",
        "--json",
    ]
    assert check.artifact_paths == (".verify-logs/contract-compatibility.json",)


def test_staged_catalog_does_not_invent_unsupported_contract_flag() -> None:
    """Catalog uses the public base-ref surface until staged mode is public."""
    check = _contract_check(staged=True)

    assert "--staged" not in check.command
    assert check.command[-5:] == ["contract", "check", "--base-ref", "HEAD", "--json"]


def test_contract_check_order_is_stable_after_verification_plan() -> None:
    """The policy gates retain one reviewable deterministic order."""
    names = [
        item.name
        for item in make_checks(MaintainerConfig(), "HEAD", "origin/main")
    ]

    assert names.index("contract-compatibility") == names.index("verification-plan-policy") + 1


def test_contract_check_is_assigned_to_static_policy_group() -> None:
    """Every CI catalog check remains explicitly partitioned."""
    check = _contract_check()

    assert checks_for_group((check,), STATIC_AND_POLICY_GROUP) == [check]


def test_missing_policy_uses_exact_optional_skip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Repositories without authored policy skip rather than fail."""
    monkeypatch.chdir(tmp_path)

    assert executor.optional_skip(_contract_check()) == f"optional skip: {OPTIONAL_REASON}"


def test_executor_retains_complete_contract_json_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verifier stdout capture preserves the complete machine-readable report."""
    artifact = tmp_path / "contract-compatibility.json"
    check = replace(
        _contract_check(),
        required_paths=(),
        optional_skip_reason=None,
        artifact_paths=(str(artifact),),
    )
    output = '{"schema_version":1,"errors":[]}\n'
    monkeypatch.setattr(
        executor,
        "run_command",
        lambda *_args, **_kwargs: (0, output),
    )

    result = executor.run_check(check, tmp_path / "logs", 50, 2_000)

    assert artifact.read_text(encoding="utf-8") == output
    assert result.artifact_paths == (str(artifact),)


def test_executor_does_not_label_non_json_output_as_contract_artifact(tmp_path: Path) -> None:
    """Preflight diagnostics cannot masquerade as a structured report."""
    artifact = tmp_path / "contract-compatibility.json"
    check = replace(_contract_check(), artifact_paths=(str(artifact),))

    executor.capture_stdout_artifact(check, "FAIL configuration\n")

    assert not artifact.exists()
