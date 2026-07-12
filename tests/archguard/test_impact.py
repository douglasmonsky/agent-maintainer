"""Tests for Archguard architecture impact analysis."""

from __future__ import annotations

from pathlib import Path

from archguard.impact import (
    ArchitectureMap,
    ModuleRule,
    OwnedModule,
    affected_tests,
    boundary_status,
    dependency_direction,
    load_architecture,
    module_rules,
    render_boundary,
    render_impact,
    render_map,
)


def write_tach_fixture(repo_root: Path) -> None:
    """Write a small Tach fixture repository."""

    package = repo_root / "src" / "sample"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text("from sample import service\n", encoding="utf-8")
    (package / "service.py").write_text("from sample import models\n", encoding="utf-8")
    (package / "models.py").write_text("VALUE = 1\n", encoding="utf-8")
    tests = repo_root / "tests"
    tests.mkdir()
    (tests / "test_service.py").write_text("def test_service(): pass\n", encoding="utf-8")
    (repo_root / "tach.toml").write_text(
        """
source_roots = ["src"]
root_module = "forbid"
layers = ["entrypoint", "runtime", "models"]

[[modules]]
path = "sample.cli"
layer = "entrypoint"

[[modules]]
path = "sample.service"
layer = "runtime"

[[modules]]
path = "sample.models"
layer = "models"
""".strip(),
        encoding="utf-8",
    )


def write_domain_fixture(repo_root: Path) -> None:
    """Write nested verify/wait ownership with local and absolute dependencies."""

    verify = repo_root / "src" / "sample" / "verify"
    wait = repo_root / "src" / "sample" / "wait"
    tests = repo_root / "tests"
    verify.mkdir(parents=True)
    wait.mkdir(parents=True)
    tests.mkdir()
    (verify / "worker.py").write_text("VALUE = 1\n", encoding="utf-8")
    (verify / "orchestrator.py").write_text("VALUE = 1\n", encoding="utf-8")
    (wait / "broker.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tests / "verify").mkdir()
    (tests / "verify" / "test_worker.py").write_text("def test_worker(): pass\n", encoding="utf-8")
    (repo_root / "tach.toml").write_text(
        'source_roots = ["src"]\nroot_module = "forbid"\n\n[[modules]]\npath = "sample"\n',
        encoding="utf-8",
    )
    (verify / "tach.domain.toml").write_text(
        "[root]\ndepends_on = []\n\n"
        '[[modules]]\npath = "worker"\ndepends_on = ["//sample.wait.broker"]\n\n'
        '[[modules]]\npath = "orchestrator"\ndepends_on = ["worker"]\n',
        encoding="utf-8",
    )
    (wait / "tach.domain.toml").write_text(
        '[root]\ndepends_on = []\n\n[[modules]]\npath = "broker"\ndepends_on = []\n',
        encoding="utf-8",
    )


def test_render_map_lists_modules_layers_and_roots(tmp_path: Path) -> None:
    """Render configured Tach module ownership map."""

    write_tach_fixture(tmp_path)
    output = render_map(load_architecture(tmp_path))

    assert "# Architecture Map" in output
    assert "Source roots: src" in output
    assert "- sample.service [runtime]" in output


def test_nested_domains_override_broad_root_ownership(tmp_path: Path) -> None:
    """Nested domains provide ownership and explicit boundary policy."""

    write_domain_fixture(tmp_path)
    architecture = load_architecture(tmp_path)

    impact = render_impact(tmp_path, architecture, Path("src/sample/verify/worker.py"))
    allowed = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/verify/worker.py"),
        Path("src/sample/wait/broker.py"),
    )
    forbidden = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/wait/broker.py"),
        Path("src/sample/verify/worker.py"),
    )

    assert "Module ownership: sample.verify.worker" in impact
    assert "sample.verify.worker" in render_map(architecture)
    assert "depends on: sample.wait.broker" in render_map(architecture)
    assert "allowed: sample.verify.worker declares sample.wait.broker" in allowed
    assert "violation: sample.wait.broker does not declare sample.verify.worker" in forbidden


def test_domain_dependencies_normalize_local_and_absolute_paths(tmp_path: Path) -> None:
    """Domain dependency declarations normalize into full module paths."""

    write_domain_fixture(tmp_path)
    architecture = load_architecture(tmp_path)
    rules = {rule.name: rule for rule in architecture.modules}

    assert rules["sample.verify.worker"].depends_on == ("sample.wait.broker",)
    assert rules["sample.verify.orchestrator"].depends_on == ("sample.verify.worker",)
    assert rules["sample.wait.broker"].depends_on == ()


def test_malformed_domain_policy_fails_boundary_explanation_closed(tmp_path: Path) -> None:
    """Incomplete nested policy never falls back to a broad allowed result."""

    write_tach_fixture(tmp_path)
    domain = tmp_path / "src" / "sample" / "broken" / "tach.domain.toml"
    domain.parent.mkdir(parents=True)
    domain.write_text("[[modules]\npath =", encoding="utf-8")

    architecture = load_architecture(tmp_path)
    output = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/cli.py"),
        Path("src/sample/models.py"),
    )

    assert architecture.load_errors == ("src/sample/broken/tach.domain.toml: invalid_toml",)
    assert "Policy load errors:" in render_map(architecture)
    assert "Dependency direction: unknown: architecture policy is incomplete" in output
    assert "allowed:" not in output


def test_malformed_root_policy_returns_bounded_error_map(tmp_path: Path) -> None:
    """Root parse failures are reported without a traceback or false policy."""

    (tmp_path / "tach.toml").write_text("[[modules]\npath =", encoding="utf-8")

    architecture = load_architecture(tmp_path)

    assert architecture.load_errors == ("tach.toml: invalid_toml",)
    assert "- tach.toml: invalid_toml" in render_map(architecture)
    assert dependency_direction(architecture, None) == (
        "unknown: architecture policy is incomplete"
    )


def test_render_impact_reports_owner_direction_and_tests(tmp_path: Path) -> None:
    """Render impact for changed source file."""

    write_tach_fixture(tmp_path)
    output = render_impact(
        tmp_path,
        load_architecture(tmp_path),
        Path("src/sample/service.py"),
    )

    assert "Module ownership: sample.service" in output
    assert "Dependency direction: runtime may depend on runtime, models" in output
    assert "Changed modules: sample.service" in output
    assert "Affected tests: tests/test_service.py" in output


def test_render_boundary_reports_allowed_and_forbidden_directions(
    tmp_path: Path,
) -> None:
    """Explain dependency direction between two owned source files."""

    write_tach_fixture(tmp_path)
    architecture = load_architecture(tmp_path)

    allowed = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/cli.py"),
        Path("src/sample/service.py"),
    )
    forbidden = render_boundary(
        tmp_path,
        architecture,
        Path("src/sample/models.py"),
        Path("src/sample/service.py"),
    )

    assert "Dependency direction: allowed: entrypoint can depend on runtime" in allowed
    assert "Dependency direction: violation: models must not depend on runtime" in forbidden


def test_module_rules_ignore_malformed_items_and_flatten_paths() -> None:
    """Defensively parse Tach module lists."""

    rules = module_rules(
        [
            "bad",
            {1: "non-string-key"},
            {"paths": ["sample.good", "", 3], "layer": "runtime"},
            {"path": "sample.cli", "layer": "entrypoint"},
            {"path": "", "layer": "runtime"},
        ],
    )

    assert rules == (
        ModuleRule(name="sample.cli", layer="entrypoint"),
        ModuleRule(name="sample.good", layer="runtime"),
    )


def test_resolved_files_report_unowned_and_init_modules(tmp_path: Path) -> None:
    """Resolve outside, non-Python, and package init paths."""

    write_tach_fixture(tmp_path)
    architecture = load_architecture(tmp_path)
    (tmp_path / "src" / "sample" / "README.md").write_text("docs", encoding="utf-8")

    outside = render_impact(tmp_path, architecture, Path("README.md"))
    non_python = render_impact(tmp_path, architecture, Path("src/sample/README.md"))
    package_init = render_impact(tmp_path, architecture, Path("src/sample/__init__.py"))

    assert "Module ownership: <unassigned>" in outside
    assert "Module ownership: <unassigned>" in non_python
    assert "Changed modules: <unassigned>" in package_init


def test_dependency_helpers_report_unknown_same_and_no_tests(tmp_path: Path) -> None:
    """Cover compact defensive architecture helper branches."""

    owner = ModuleRule(name="sample.service", layer="runtime")
    missing_layer = ModuleRule(name="sample.unknown", layer="unknown")
    architecture = ArchitectureMap(
        source_roots=("src",),
        layers=("entrypoint", "runtime", "models"),
        modules=(owner, missing_layer),
    )

    assert dependency_direction(architecture, None) == "unknown"
    assert boundary_status(architecture, None, owner).startswith("unknown")
    assert boundary_status(architecture, owner, owner) == "same module"
    assert boundary_status(architecture, missing_layer, owner).startswith("unknown")
    assert affected_tests(tmp_path, OwnedModule(Path("x.py"), "x", None)) == "none found"
    assert (
        affected_tests(tmp_path, OwnedModule(Path("x.py"), "sample.service", owner)) == "none found"
    )
