"""Tests for maintainer setup diagnostics."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import policy as maintainer_doctor_policy


def write_repo_root(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "maintainer.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    return tmp_path


def test_optional_gates_warn_for_legacy_defaults(tmp_path: Path) -> None:
    result = maintainer_doctor.check_optional_gates(tmp_path, MaintainerConfig())

    assert result.status == maintainer_doctor.WARNING
    assert ".importlinter" in result.message
    assert "pip-audit disabled" in result.message
    assert "interrogate disabled" in result.message


def test_optional_gates_pass_when_enabled(tmp_path: Path) -> None:
    (tmp_path / ".importlinter").write_text("[importlinter]\n", encoding="utf-8")
    config = MaintainerConfig(
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
        enable_sbom=True,
        enable_license_check=True,
    )

    result = maintainer_doctor.check_optional_gates(tmp_path, config)

    assert result.status == maintainer_doctor.OK
    assert "sbom" in result.message
    assert "license-check" in result.message


def test_optional_gates_warn_when_tach_config_is_missing(tmp_path: Path) -> None:
    config = MaintainerConfig(
        architecture_tool="tach",
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = maintainer_doctor.check_optional_gates(tmp_path, config)

    assert result.status == maintainer_doctor.WARNING
    assert "tach.toml is absent" in result.message


def test_optional_gates_warn_when_fresh_strict_tach_is_permissive(tmp_path: Path) -> None:
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "ignore"

[[modules]]
path = "scripts"
""".strip(),
        encoding="utf-8",
    )
    config = MaintainerConfig(
        mode="fresh-strict",
        architecture_tool="tach",
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = maintainer_doctor.check_optional_gates(tmp_path, config)

    assert result.status == maintainer_doctor.WARNING
    assert 'root_module = "forbid"' in result.message


def test_optional_gates_pass_when_tach_is_strict(tmp_path: Path) -> None:
    scripts_path = tmp_path / "scripts"
    scripts_path.mkdir()
    (scripts_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "forbid"

[[modules]]
path = "scripts"
""".strip(),
        encoding="utf-8",
    )
    config = MaintainerConfig(
        mode="fresh-strict",
        architecture_tool="tach",
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = maintainer_doctor.check_optional_gates(tmp_path, config)

    assert result.status == maintainer_doctor.OK
    assert "Tach" in result.message


def test_pip_audit_safety_warns_or_fails_for_empty_args() -> None:
    custom = MaintainerConfig(enable_pip_audit=True, pip_audit_args=())
    strict = MaintainerConfig(mode="fresh-strict", enable_pip_audit=True, pip_audit_args=())
    safe = MaintainerConfig(enable_pip_audit=True, pip_audit_args=("-r", "requirements.txt"))

    assert (
        maintainer_doctor_policy.check_pip_audit_safety(custom).status == maintainer_doctor.WARNING
    )
    assert maintainer_doctor_policy.check_pip_audit_safety(strict).status == maintainer_doctor.ERROR
    assert maintainer_doctor_policy.check_pip_audit_safety(safe).status == maintainer_doctor.OK


def test_secret_scanning_policy_reports_disabled_active_and_invalid() -> None:
    disabled = MaintainerConfig(enable_secret_scanning=False)
    active = MaintainerConfig(enable_secret_scanning=True, secret_scanner="gitleaks")
    unsupported = MaintainerConfig(enable_secret_scanning=True, secret_scanner="betterleaks")
    invalid_profile = MaintainerConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=("full", "unknown"),
    )

    assert (
        maintainer_doctor_policy.check_secret_scanning_policy(disabled).status
        == maintainer_doctor.OK
    )
    assert (
        maintainer_doctor_policy.check_secret_scanning_policy(active).status == maintainer_doctor.OK
    )
    assert maintainer_doctor_policy.check_secret_scanning_policy(unsupported).status == (
        maintainer_doctor.ERROR
    )
    assert maintainer_doctor_policy.check_secret_scanning_policy(invalid_profile).status == (
        maintainer_doctor.ERROR
    )
