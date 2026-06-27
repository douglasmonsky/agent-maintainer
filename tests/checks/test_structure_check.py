"""Tests folder-level structure cohesion checker."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.checks import structure as check_structure


def write_modules(folder: Path, names: list[str]) -> list[Path]:
    """Write Python modules and return their paths."""

    folder.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in names:
        path = folder / f"{name}.py"
        path.write_text("# test module\n", encoding="utf-8")
        paths.append(path)
    return paths


def test_structure_findings_warn_with_regex_and_layer_hints(tmp_path: Path) -> None:
    files = write_modules(
        tmp_path / "scripts",
        [
            "maintainer_args",
            "maintainer_config",
            "maintainer_doctor",
            "maintainer_executor",
            "other",
        ],
    )

    findings = check_structure.structure_findings(
        files,
        warn_threshold=5,
        block_threshold=0,
        patterns=(r"^maintainer_",),
        cluster_min=3,
    )

    assert len(findings) == 1
    assert findings[0].severity == check_structure.WARN
    assert any("pattern '^maintainer_'" in hint for hint in findings[0].hints)
    assert any("layer words" in hint for hint in findings[0].hints)


def test_structure_findings_block_at_configured_threshold(tmp_path: Path) -> None:
    files = write_modules(tmp_path / "scripts", ["one", "two", "three"])

    findings = check_structure.structure_findings(
        files,
        warn_threshold=2,
        block_threshold=3,
        patterns=(),
        cluster_min=2,
    )

    assert findings[0].severity == check_structure.FAIL


def test_python_files_ignore_configured_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    write_modules(tmp_path / "src", ["kept"])
    write_modules(tmp_path / "tests", ["ignored"])

    files = check_structure.python_files(("src", "tests"), ("tests/**",))

    assert files == [Path("src/kept.py")]


def test_python_files_allow_explicit_registry_exemptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    write_modules(tmp_path / "src" / "plugins", ["alpha", "beta"])

    files = check_structure.python_files(("src",), ("src/plugins/**",))

    assert files == []


def test_main_returns_success_for_warning_and_failure_for_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    write_modules(tmp_path / "src", ["one", "two", "three"])
    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")

    warning_status = check_structure.main(
        ["src", "--warn-threshold", "2", "--block-threshold", "0"]
    )
    failure_status = check_structure.main(
        ["src", "--warn-threshold", "2", "--block-threshold", "3"]
    )

    output = capsys.readouterr().out
    assert warning_status == 0
    assert failure_status == 1
    assert "Consider splitting by responsibility" in output
