"""Tests bounded root and nested Tach configuration loading failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from archguard import tach_config


def test_tach_config_issues_reports_bounded_invalid_toml(tmp_path: Path) -> None:
    """Report invalid root TOML without exposing parser details."""

    (tmp_path / "tach.toml").write_text("source_roots = [", encoding="utf-8")

    assert tach_config.tach_config_issues(tmp_path, require_strict_root=True) == [
        "tach.toml: invalid_toml"
    ]


def test_tach_config_issues_reports_bounded_invalid_utf8(tmp_path: Path) -> None:
    """Report an invalid root encoding without exposing file content."""

    (tmp_path / "tach.toml").write_bytes(b"\xff")

    assert tach_config.tach_config_issues(tmp_path, require_strict_root=True) == [
        "tach.toml: invalid_utf8"
    ]


def test_tach_config_issues_reports_bounded_read_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a root read failure without exposing operating-system details."""

    config_path = tmp_path / "tach.toml"
    config_path.write_text("root_module = 'forbid'", encoding="utf-8")
    original_read_text = Path.read_text

    def raise_for_root(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if path == config_path:
            raise OSError("private read failure")
        return original_read_text(path, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "read_text", raise_for_root)

    assert tach_config.tach_config_issues(tmp_path, require_strict_root=True) == [
        "tach.toml: read_error"
    ]


def test_tach_config_issues_reports_malformed_nested_domain(tmp_path: Path) -> None:
    """Report a bounded error when nested domain policy cannot be parsed."""

    package = tmp_path / "src" / "package"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "tach.domain.toml").write_text("[[modules]\npath =", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["src"]
root_module = "forbid"

[[modules]]
path = "package"
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    assert tach_config.tach_config_issues(tmp_path, require_strict_root=True) == [
        "src/package/tach.domain.toml: invalid_toml"
    ]
