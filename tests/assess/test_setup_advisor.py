"""Tests setup advisor recommendations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.assess.setup_advisor import build_setup_report

MANY_SOURCE_FILES = 45
AGENT_HEAVY_FILES = 25
TEXT_ENCODING = "utf-8"
TYPESCRIPT_SETUP_SCRIPT_FIXTURES = (
    {
        "lint": "pnpm exec eslint . --format json",
        "typecheck": "pnpm exec tsc --pretty false --noEmit",
        "test": "pnpm exec vitest run --reporter=json --coverage",
    },
    {
        "eslint": "eslint . --format json",
        "tsc": "tsc --pretty false --noEmit",
        "vitest": "vitest run --reporter=json --coverage",
    },
    {
        "lint": "next lint",
        "type-check": "tsc --pretty false --noEmit",
        "test:unit": "jest --json --coverage",
    },
)


def test_setup_advisor_recommends_agent_track(tmp_path: Path) -> None:
    """Agent assets produce agent track recommendation and setup prompts."""
    write_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("Read local guidance.\n", encoding=TEXT_ENCODING)
    (tmp_path / ".codex" / "hooks").mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "agent"
    assert report.preset == "strict-new-repo"
    assert report.confidence == "high"
    assert any(gate.name == "pip-audit" for gate in report.optional_gates)
    assert any("architecture boundaries" in prompt for prompt in report.agent_prompts)


def test_setup_advisor_json_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Setup advisor CLI renders stable JSON."""
    write_repo(tmp_path)

    status = cli.main(["setup", "--target", str(tmp_path), "--json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["track"] == "core"
    assert payload["preset"] == "strict-new-repo"
    assert payload["evidence"]["has_agent_config"] is True
    assert payload["evidence"]["package_workspace"] == {
        "manager_signals": [],
        "workspace_declarations": [],
        "issues": [],
        "unambiguous_manager": "",
        "ambiguous": False,
    }


def test_setup_advisor_inspects_non_python_repo(tmp_path: Path) -> None:
    """Non-Python targets stay low-confidence and dry-run first."""
    (tmp_path / "package.json").write_text("{}", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "inspect"
    assert report.preset == "manual-review"
    assert report.confidence == "low"
    assert any("No Python package" in reason for reason in report.reasons)
    assert report.next_commands == (
        "agent-maintainer assess setup --target . --json",
        "agent-maintainer init --track core --dry-run",
        "Ask an agent to identify the repo language, test command, and generated paths.",
    )


def test_setup_advisor_recommends_hardening_track(tmp_path: Path) -> None:
    """CI plus config files can justify the hardening track."""

    write_repo(tmp_path)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "verify.yml").write_text(
        "name: verify\n",
        encoding=TEXT_ENCODING,
    )
    (tmp_path / "config.yml").write_text("enabled: true\n", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "hardening"
    assert any(gate.name == "yamllint" for gate in report.optional_gates)


# docsync:evidence.start evidence.setup_advisor.recommendation_tests
def test_setup_advisor_recommends_ts_scripts(tmp_path: Path) -> None:
    """Relevant package scripts produce explicit TypeScript provider advice."""
    write_repo(tmp_path)
    write_package_scripts(tmp_path, ("lint", "typecheck", "test"))

    report = build_setup_report(collect_evidence(tmp_path))
    gates = {gate.name: gate for gate in report.optional_gates}

    assert "osv-scanner" in gates
    assert "typescript-provider" in gates
    assert "ESLint JSON" in gates["typescript-provider"].reason
    assert "tsc --pretty false" in gates["typescript-provider"].reason
    assert "Jest/Vitest JSON" in gates["typescript-provider"].reason
    assert "coverage-summary.json or lcov.info" in gates["typescript-provider"].reason
    assert "[tool.agent_maintainer.workspaces.<name>]" in (gates["typescript-provider"].reason)
    assert "package-specific checks" in gates["typescript-provider"].reason
    assert any("explicit TypeScript provider" in prompt for prompt in report.agent_prompts)
    assert any("repair facts" in prompt for prompt in report.agent_prompts)


@pytest.mark.parametrize(
    "scripts",
    TYPESCRIPT_SETUP_SCRIPT_FIXTURES,
    ids=("pnpm-vite", "vite-vitest", "next-jest"),
)
def test_setup_advisor_recommends_ts_script_fixtures(
    tmp_path: Path,
    scripts: dict[str, str],
) -> None:
    """Common TypeScript app script shapes stay advisory and explicit."""
    write_repo(tmp_path)
    write_package_script_commands(tmp_path, scripts)

    evidence = collect_evidence(tmp_path)
    report = build_setup_report(evidence)
    gates = {gate.name: gate for gate in report.optional_gates}

    assert evidence.package_scripts == tuple(sorted(scripts))
    assert "typescript-provider" in gates
    assert "mapped to explicit TypeScript provider commands" in (
        gates["typescript-provider"].reason
    )
    assert "[tool.agent_maintainer.workspaces.<name>]" in (gates["typescript-provider"].reason)


def test_setup_advisor_ignores_nested_package_scripts(tmp_path: Path) -> None:
    """Nested package scripts do not imply root command ownership."""
    write_repo(tmp_path)
    nested = tmp_path / "packages" / "web"
    nested.mkdir(parents=True)
    write_package_script_commands(
        nested,
        {
            "lint": "pnpm exec eslint . --format json",
            "typecheck": "pnpm exec tsc --pretty false --noEmit",
            "test": "pnpm exec vitest run --reporter=json --coverage",
        },
    )

    evidence = collect_evidence(tmp_path)
    report = build_setup_report(evidence)
    gate_names = {gate.name for gate in report.optional_gates}

    assert evidence.package_scripts == ()
    assert "typescript-provider" not in gate_names


def test_setup_advisor_ignores_irrelevant_scripts(tmp_path: Path) -> None:
    """Package scripts alone do not imply TypeScript provider setup."""
    write_repo(tmp_path)
    write_package_scripts(tmp_path, ("build", "preview"))

    report = build_setup_report(collect_evidence(tmp_path))
    gate_names = {gate.name for gate in report.optional_gates}

    assert "osv-scanner" in gate_names
    assert "typescript-provider" not in gate_names


def test_setup_advisor_explains_corroborated_package_workspace_evidence(
    tmp_path: Path,
) -> None:
    write_package_script_commands(
        tmp_path,
        {
            "lint": "eslint .",
            "typecheck": "tsc --noEmit",
            "test": "vitest run",
        },
        package_manager="pnpm@9.15.0",
        workspaces=("packages/*",),
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "inspect"
    assert report.preset == "manual-review"
    assert any(
        "advisory package-manager evidence for `pnpm`" in reason for reason in report.reasons
    )
    assert any(
        "workspace declaration" in reason and "unexpanded" in reason for reason in report.reasons
    )
    assert any("explicit root or workspace commands" in prompt for prompt in report.agent_prompts)


def test_setup_advisor_keeps_conflicting_manager_evidence_advisory(tmp_path: Path) -> None:
    write_package_script_commands(
        tmp_path,
        {"test": "vitest run"},
        package_manager="pnpm@9.15.0",
    )
    (tmp_path / "yarn.lock").write_text("", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "inspect"
    assert report.evidence.package_workspace.ambiguous is True
    assert any("no package manager was selected" in reason for reason in report.reasons)
    assert any(
        "Resolve package-manager evidence conflicts" in prompt for prompt in report.agent_prompts
    )
    assert {gate.name for gate in report.optional_gates} >= {"typescript-provider"}


# docsync:evidence.end evidence.setup_advisor.recommendation_tests


def test_setup_advisor_recommends_legacy_ratchet(tmp_path: Path) -> None:
    """Large untested repos should start with legacy-ratchet adoption."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'legacy'\n",
        encoding=TEXT_ENCODING,
    )
    package = tmp_path / "src" / "legacy"
    package.mkdir(parents=True)
    for index in range(MANY_SOURCE_FILES):
        (package / f"module_{index}.py").write_text("VALUE = 1\n", encoding=TEXT_ENCODING)

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "core"
    assert report.preset == "legacy-ratchet"
    assert any("No test tree" in reason for reason in report.reasons)
    assert any("smallest behavior surface" in prompt for prompt in report.agent_prompts)


def test_setup_advisor_agent_heavy_preset(tmp_path: Path) -> None:
    """Mature agent repos can get the ai-agent-heavy preset."""

    write_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("Read local guidance.\n", encoding=TEXT_ENCODING)
    package = tmp_path / "src" / "example"
    tests = tmp_path / "tests"
    for index in range(AGENT_HEAVY_FILES):
        (package / f"module_{index}.py").write_text("VALUE = 1\n", encoding=TEXT_ENCODING)
        (tests / f"test_module_{index}.py").write_text(
            "def test_value():\n    assert True\n",
            encoding=TEXT_ENCODING,
        )

    report = build_setup_report(collect_evidence(tmp_path))

    assert report.track == "agent"
    assert report.preset == "ai-agent-heavy"


def write_repo(root: Path) -> None:
    """Write a minimal Python repo fixture."""
    (root / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
mode = "custom"
""".strip(),
        encoding=TEXT_ENCODING,
    )
    package = root / "src" / "example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding=TEXT_ENCODING)
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text(
        "def test_example():\n    assert True\n",
        encoding=TEXT_ENCODING,
    )


def write_package_scripts(root: Path, script_names: tuple[str, ...]) -> None:
    """Write a package.json with named scripts."""
    write_package_script_commands(root, {name: f"echo {name}" for name in script_names})


def write_package_script_commands(
    root: Path,
    scripts: dict[str, str],
    *,
    package_manager: str = "",
    workspaces: tuple[str, ...] = (),
) -> None:
    """Write root package metadata used by setup-advisor tests."""
    payload: dict[str, object] = {"scripts": scripts}
    if package_manager:
        payload["packageManager"] = package_manager
    if workspaces:
        payload["workspaces"] = list(workspaces)
    (root / "package.json").write_text(json.dumps(payload), encoding=TEXT_ENCODING)
