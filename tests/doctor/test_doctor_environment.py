"""Tests for doctor environment and artifact hygiene checks."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor import setup as maintainer_doctor_setup
from agent_maintainer.doctor.support import dogfood as maintainer_doctor_dogfood
from agent_maintainer.doctor.support import models as maintainer_doctor_models

ENCODING = "utf-8"


def write_local_package(repo_root: Path) -> Path:
    """Create a minimal local package for dogfood checks."""

    package_init = repo_root / "src" / "agent_maintainer" / "__init__.py"
    package_init.parent.mkdir(parents=True)
    package_init.write_text("", encoding=ENCODING)
    return package_init


def test_source_dogfood_skips_without_package(
    tmp_path: Path,
) -> None:
    """Repos without local source package do not trigger dogfood checks."""

    result = maintainer_doctor_setup.check_source_checkout_dogfood(tmp_path)

    assert result.status == maintainer_doctor.OK
    assert result.state == maintainer_doctor_models.NOT_APPLICABLE


def test_source_dogfood_passes_local_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Source checkout passes when import resolves to local src package."""

    package_init = write_local_package(tmp_path)
    monkeypatch.setattr(
        maintainer_doctor_setup.importlib_util,
        "find_spec",
        lambda _name: SimpleNamespace(origin=str(package_init)),
    )

    result = maintainer_doctor_setup.check_source_checkout_dogfood(tmp_path)

    assert result.status == maintainer_doctor.OK
    assert "local src/agent_maintainer" in result.message


def test_source_dogfood_warns_stale_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Source checkout fails when import resolves outside local src package."""

    write_local_package(tmp_path)
    stale_path = tmp_path / ".venv" / "lib" / "site-packages" / "agent_maintainer"
    monkeypatch.setattr(
        maintainer_doctor_setup.importlib_util,
        "find_spec",
        lambda _name: SimpleNamespace(origin=str(stale_path)),
    )

    result = maintainer_doctor_setup.check_source_checkout_dogfood(tmp_path)

    assert result.status == maintainer_doctor.ERROR
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert "python -m pip install -e ." in result.hint


def test_console_dogfood_skips_without_package(tmp_path: Path) -> None:
    """Console dogfood check skips repos without local package."""
    result = maintainer_doctor_setup.check_console_script_dogfood(tmp_path)
    assert result.status == maintainer_doctor.OK
    assert result.state == maintainer_doctor_models.NOT_APPLICABLE


def test_console_dogfood_skips_without_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Console dogfood check skips when console script is unavailable."""

    write_local_package(tmp_path)
    monkeypatch.setattr(
        maintainer_doctor_dogfood.shutil,
        "which",
        lambda _name: None,
    )
    result = maintainer_doctor_setup.check_console_script_dogfood(tmp_path)
    assert result.status == maintainer_doctor.OK
    assert result.state == maintainer_doctor_models.NOT_APPLICABLE
    bad_script = tmp_path / "agent-maintainer"
    bad_script.write_text("#!/bin/sh\n", encoding=ENCODING)
    assert maintainer_doctor_dogfood.console_script_python(bad_script) is None
    assert maintainer_doctor_dogfood.console_script_import_path(bad_script) is None


def test_console_dogfood_warns_uninspectable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Console dogfood check warns when script target cannot be inspected."""
    write_local_package(tmp_path)
    script_path = tmp_path / "bin" / "agent-maintainer"
    monkeypatch.setattr(
        maintainer_doctor_dogfood.shutil,
        "which",
        lambda _name: str(script_path),
    )
    monkeypatch.setattr(
        maintainer_doctor_dogfood,
        "console_script_import_path",
        lambda _script_path: None,
    )
    result = maintainer_doctor_setup.check_console_script_dogfood(tmp_path)
    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.MISSING


def test_console_dogfood_passes_local_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Console dogfood check passes when script resolves local package."""

    package_init = write_local_package(tmp_path)
    script_path = tmp_path / "bin" / "agent-maintainer"
    script_path.parent.mkdir(parents=True)
    script_path.write_text(f"#!{sys.executable}\n", encoding=ENCODING)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "src"))
    monkeypatch.setattr(
        maintainer_doctor_dogfood.shutil,
        "which",
        lambda _name: str(script_path),
    )
    result = maintainer_doctor_setup.check_console_script_dogfood(tmp_path)
    assert result.status == maintainer_doctor.OK
    assert result.message.endswith("local src/agent_maintainer.")
    assert maintainer_doctor_dogfood.console_script_import_path(script_path) == (
        package_init.resolve()
    )


def test_console_dogfood_warns_stale_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Console dogfood check warns when script resolves stale package."""
    write_local_package(tmp_path)
    script_path = tmp_path / "bin" / "agent-maintainer"
    stale_path = tmp_path / "site-packages" / "agent_maintainer" / "__init__.py"
    stale_path.parent.mkdir(parents=True)
    stale_path.write_text("", encoding=ENCODING)
    monkeypatch.setattr(
        maintainer_doctor_dogfood.shutil,
        "which",
        lambda _name: str(script_path),
    )
    monkeypatch.setattr(
        maintainer_doctor_dogfood,
        "console_script_import_path",
        lambda _script_path: stale_path,
    )
    result = maintainer_doctor_setup.check_console_script_dogfood(tmp_path)
    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert result.hint == "Run python -m pip install -e ."


def test_console_helpers_handle_failed_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Console helper functions skip failed or invalid script probes."""
    script_path = tmp_path / "agent-maintainer"
    script_path.write_text(f"#!{sys.executable}\n", encoding=ENCODING)
    monkeypatch.setattr(
        maintainer_doctor_dogfood.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""),
    )
    no_shebang = tmp_path / "plain-script"
    no_shebang.write_text("python\n", encoding=ENCODING)
    assert maintainer_doctor_dogfood.console_script_import_path(script_path) is None
    assert maintainer_doctor_dogfood.console_script_python(no_shebang) is None
    assert maintainer_doctor_dogfood.console_script_python(tmp_path / "missing") is None


def test_dupe_artifacts_pass_when_absent(tmp_path: Path) -> None:
    """Doctor passes when no macOS-style duplicate artifact names are present."""
    (tmp_path / "src" / "agent_maintainer").mkdir(parents=True)
    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)
    assert result.status == maintainer_doctor.OK


def test_dupe_artifacts_warn_when_present(tmp_path: Path) -> None:
    """Doctor warns for likely duplicate generated artifact names."""
    duplicate = tmp_path / "src" / "agent_maintainer" / "verify 2.py"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("", encoding=ENCODING)
    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)
    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert "src/agent_maintainer/verify 2.py" in result.message


def test_dupe_artifacts_warn_for_copy_names(tmp_path: Path) -> None:
    """Doctor warns for generated copy-style artifact names."""
    duplicate = tmp_path / ".verify-logs" / "manifest copy 2.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("{}", encoding=ENCODING)
    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)
    assert result.status == maintainer_doctor.WARNING
    assert ".verify-logs/manifest copy 2.json" in result.message


def test_dupe_artifacts_warn_for_git_metadata_copies(tmp_path: Path) -> None:
    """Doctor warns local Git metadata copy artifacts without scanning internals."""
    duplicate = tmp_path / ".git" / "index 2"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("duplicate index", encoding=ENCODING)

    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert ".git/index 2" in result.message


def test_dupe_artifacts_warn_for_python_bytecode_cache(tmp_path: Path) -> None:
    """Doctor warns generated Python bytecode caches under scanned roots."""
    cache_dir = tmp_path / "src" / "agent_maintainer" / "__pycache__"
    cache_dir.mkdir(parents=True)
    bytecode = cache_dir / "runtime.cpython-313.pyc"
    bytecode.write_bytes(b"bytecode")

    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert "src/agent_maintainer/__pycache__" in result.message


def test_dupe_artifacts_warn_for_python_bytecode_file(tmp_path: Path) -> None:
    """Doctor warns generated Python bytecode files even without cache dir hit."""
    bytecode = tmp_path / "tests" / "example.cpython-313.pyc"
    bytecode.parent.mkdir(parents=True)
    bytecode.write_bytes(b"bytecode")

    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert "tests/example.cpython-313.pyc" in result.message


def test_dupe_artifacts_include_change_plans(tmp_path: Path) -> None:
    """Doctor warns for duplicate change-plan copies from local tools."""
    duplicate = tmp_path / ".agent-maintainer" / "change-plans" / "plan 2.md"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("", encoding=ENCODING)
    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)
    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert ".agent-maintainer/change-plans/plan 2.md" in result.message


def test_dupe_artifacts_include_verify_logs(tmp_path: Path) -> None:
    """Doctor warns for duplicate verifier artifacts under diagnostics."""
    duplicate = tmp_path / ".verify-logs" / "secret-scan-full 2.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("[]", encoding=ENCODING)
    result = maintainer_doctor_setup.check_duplicate_generated_artifacts(tmp_path)
    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert ".verify-logs/secret-scan-full 2.json" in result.message
