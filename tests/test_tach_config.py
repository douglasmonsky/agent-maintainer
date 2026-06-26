"""Tests Tach architecture configuration validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails import tach as guardrail_tach
from ai_guardrails.checks import tach_config as check_tach_config


def test_tach_config_issues_require_modules_and_strict_root(tmp_path: Path) -> None:
    """Require strict root ownership and at least one configured module."""
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "ignore"
""".strip(),
        encoding="utf-8",
    )

    issues = guardrail_tach.tach_config_issues(tmp_path, require_strict_root=True)

    assert "tach.toml must define at least one module" in issues
    assert 'tach.toml must set root_module = "forbid"' in issues


def test_tach_config_issues_require_explicit_source_modules(tmp_path: Path) -> None:
    """Require each source file to be assigned in tach.toml."""
    package_path = tmp_path / "package"
    package_path.mkdir()
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "known.py").write_text("", encoding="utf-8")
    (package_path / "stale.py").write_text("", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_stale.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "forbid"
exclude = ["tests/"]

[[modules]]
path = "package"

[[modules]]
path = "package.known"
""".strip(),
        encoding="utf-8",
    )

    issues = guardrail_tach.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == ["tach.toml must explicitly assign source modules: package.stale"]


def test_tach_config_issues_truncates_many_missing_modules(tmp_path: Path) -> None:
    """Keep stale ownership messages compact when many modules are missing."""
    package_path = tmp_path / "package"
    package_path.mkdir()
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "known.py").write_text("", encoding="utf-8")
    for index in range(6):
        (package_path / f"stale_{index}.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = [".", "missing"]
root_module = "forbid"

[[modules]]
paths = ["package.known"]
""".strip(),
        encoding="utf-8",
    )

    issues = guardrail_tach.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == [
        "tach.toml must explicitly assign source modules: "
        "package.stale_0, package.stale_1, package.stale_2, "
        "package.stale_3, package.stale_4, ... (1 more)"
    ]


def test_tach_config_issues_rejects_missing_module_references(tmp_path: Path) -> None:
    """Reject module entries that no longer resolve to source files."""
    package_path = tmp_path / "package"
    package_path.mkdir()
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "known.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "forbid"

[[modules]]
paths = ["package.known", "package.missing"]
""".strip(),
        encoding="utf-8",
    )

    issues = guardrail_tach.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == ["tach.toml references modules without source files: package.missing"]


def test_tach_config_issues_reports_malformed_module_items(tmp_path: Path) -> None:
    """Reject malformed module table entries."""
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "forbid"
modules = ["not-a-module-table"]
""".strip(),
        encoding="utf-8",
    )

    issues = guardrail_tach.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == ["each tach module must define path or paths"]


def test_tach_config_defensive_helpers_handle_invalid_inputs(tmp_path: Path) -> None:
    """Keep defensive helper branches stable for malformed TOML values."""
    assert guardrail_tach._source_module_names(tmp_path, "scripts", None) == ()
    assert not guardrail_tach._matches_exclude("package/file.py", ("package",), " ")


def test_tach_config_main_reports_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Report success when strict Tach configuration is internally consistent."""
    monkeypatch.chdir(tmp_path)
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

    assert check_tach_config.main([]) == 0
    output = capsys.readouterr().out
    assert "tach.toml" in output
    assert "configured" in output
