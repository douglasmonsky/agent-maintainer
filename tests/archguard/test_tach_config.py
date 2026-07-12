"""Tests Tach architecture configuration validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from archguard import tach_config, tach_config_domains, tach_config_sources
from archguard.cli import tach_config_main


def test_tach_config_issues_require_modules_and_strict_root(tmp_path: Path) -> None:
    """Require strict root ownership and at least one configured module."""
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "ignore"
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert "tach.toml must define at least one module" in issues
    assert 'tach.toml must set root_module = "forbid"' in issues


def test_tach_config_issues_reports_invalid_toml(tmp_path: Path) -> None:
    """Report invalid Tach TOML before deeper validation."""
    (tmp_path / "tach.toml").write_text("source_roots = [", encoding="utf-8")

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues[0].startswith("tach.toml invalid:")


def test_tach_config_issues_requires_source_roots(tmp_path: Path) -> None:
    """Require Tach source roots to make ownership checks meaningful."""
    (tmp_path / "tach.toml").write_text(
        """
root_module = "forbid"

[[modules]]

path = "package"
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert "tach.toml must define source_roots" in issues


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
depends_on = []

[[modules]]
path = "package.known"
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == ["tach.toml must explicitly list source modules: package.stale"]


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
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == [
        "tach.toml must explicitly list source modules: "
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
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

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

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == ["each tach.toml module must define path or paths"]


def test_tach_config_issues_require_dependency_contracts(tmp_path: Path) -> None:
    """Require modules to declare dependency contracts, even when empty."""
    package_path = tmp_path / "package"
    package_path.mkdir()
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "known.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "forbid"

[[modules]]
path = "package.known"
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == ["each tach.toml module must define depends_on: package.known"]


def test_tach_config_issues_rejects_large_path_groups(tmp_path: Path) -> None:
    """Reject broad path buckets that hide architecture ownership."""
    package_path = tmp_path / "package"
    package_path.mkdir()
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    module_names = [f"module_{index}" for index in range(9)]
    for module_name in module_names:
        (package_path / f"{module_name}.py").write_text("", encoding="utf-8")
    configured_paths = ", ".join(f'"package.{module_name}"' for module_name in module_names)
    (tmp_path / "tach.toml").write_text(
        f"""
source_roots = ["."]
root_module = "forbid"

[[modules]]
paths = [{configured_paths}]
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == [
        "tach.toml module path groups must be <= 8 paths: package.module_0",
    ]


def test_tach_config_issues_validates_domain_root_and_module_shape(
    tmp_path: Path,
) -> None:
    """Validate domain-file root and module table shape."""
    package_path = tmp_path / "src" / "package"
    package_path.mkdir(parents=True)
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "module.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["src"]
root_module = "forbid"

[[modules]]
path = "package.module"
depends_on = []
""".strip(),
        encoding="utf-8",
    )
    (package_path / "tach.domain.toml").write_text(
        """
modules = "not-a-list"

[root]
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == [
        "tach.domain.toml root depends_on missing: package",
        "tach.domain.toml modules must be a list: package",
    ]


def test_tach_domain_root_owns_descendant_source_modules(tmp_path: Path) -> None:
    """Treat a domain root as explicit ownership of its package descendants."""
    package_path = tmp_path / "src" / "package"
    package_path.mkdir(parents=True)
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "service.py").write_text("", encoding="utf-8")
    (package_path / "nested").mkdir()
    (package_path / "nested" / "worker.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "unowned.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["src"]
root_module = "ignore"

[[modules]]
path = "unowned"
depends_on = []
""".strip(),
        encoding="utf-8",
    )
    (package_path / "tach.domain.toml").write_text(
        """
[root]
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=False)

    assert issues == []


def test_tach_domain_root_does_not_own_sibling_modules(tmp_path: Path) -> None:
    """Continue reporting source modules outside every explicit domain root."""
    package_path = tmp_path / "src" / "package"
    package_path.mkdir(parents=True)
    (package_path / "service.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "entrypoint.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "unowned.py").write_text("", encoding="utf-8")
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["src"]
root_module = "ignore"

[[modules]]
path = "entrypoint"
depends_on = []
""".strip(),
        encoding="utf-8",
    )
    (package_path / "tach.domain.toml").write_text(
        """
[root]
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=False)

    assert issues == ["tach.toml must explicitly list source modules: unowned"]


def test_tach_config_issues_validates_domain_module_contracts(
    tmp_path: Path,
) -> None:
    """Validate domain-file dependency contracts and broad path groups."""
    package_path = tmp_path / "src" / "package"
    package_path.mkdir(parents=True)
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    module_names = [f"module_{index}" for index in range(9)]
    for module_name in module_names:
        (package_path / f"{module_name}.py").write_text("", encoding="utf-8")
    configured_paths = ", ".join(f'"{module_name}"' for module_name in module_names)
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
    (package_path / "tach.domain.toml").write_text(
        f"""
[root]
depends_on = []

[[modules]]
paths = [{configured_paths}]
""".strip(),
        encoding="utf-8",
    )

    issues = tach_config.tach_config_issues(tmp_path, require_strict_root=True)

    assert issues == [
        "each tach.domain.toml module must define depends_on: module_0",
        "tach.domain.toml module path groups must be <= 8 paths: module_0",
    ]


def test_tach_domain_helpers_expand_domain_local_paths(tmp_path: Path) -> None:
    """Expand domain roots and domain-local module paths."""
    package_path = tmp_path / "src" / "package"
    package_path.mkdir(parents=True)
    (package_path / "tach.domain.toml").write_text(
        """
[root]
depends_on = []
""".strip(),
        encoding="utf-8",
    )
    ignored_path = tmp_path / "src" / "ignored"
    ignored_path.mkdir()
    (ignored_path / "tach.domain.toml").write_text("root = [", encoding="utf-8")

    payloads = tach_config_domains.load_domain_payloads(tmp_path, ["src"]).payloads

    assert payloads == (("package", {"root": {"depends_on": []}}),)
    assert tach_config_domains.domain_module_path("package", ".") == "package"
    assert tach_config_domains.domain_module_path("package", "module") == ("package.module")
    assert tach_config_domains.configured_domain_module_paths(
        (
            (
                "package",
                {
                    "root": {},
                    "modules": [
                        42,
                        {"path": "."},
                        {"path": "service"},
                        {"paths": ["models", "views"]},
                    ],
                },
            ),
        )
    ) == frozenset(
        {
            "package",
            "package.service",
            "package.models",
            "package.views",
        }
    )


def test_tach_config_defensive_helpers_handle_invalid_inputs(tmp_path: Path) -> None:
    """Keep defensive helper branches stable for malformed TOML values."""
    assert tach_config_sources.source_module_names(tmp_path, "scripts", None) == ()
    assert tach_config_sources.configured_module_paths(
        [None, {1: "invalid"}, {"path": "package.good"}],
    ) == frozenset(("package.good",))
    assert not tach_config_sources.module_has_path({1: "invalid"})
    assert not tach_config_sources.matches_exclude("package/file.py", ("package",), " ")


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
depends_on = []
""".strip(),
        encoding="utf-8",
    )

    assert tach_config_main([]) == 0
    output = capsys.readouterr().out
    assert "tach.toml" in output
    assert "configured" in output
