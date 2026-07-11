"""Existing-application onboarding fixture contract tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_maintainer.core.scaffold import initializer, transaction

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "existing_app_onboarding"
EXPECTED_PYTHON_LAYOUT_COUNT = 2


@dataclass(frozen=True)
class ExistingApplicationCase:
    """Expected onboarding behavior for one representative application."""

    name: str
    track: str
    python_path: str
    expected_plan: tuple[str, ...]
    preserved_paths: tuple[str, ...]
    backup_paths: tuple[str, ...]
    merged_fragments: tuple[tuple[str, tuple[str, ...]], ...]


CASES = (
    ExistingApplicationCase(
        name="src-library",
        track="core",
        python_path="src",
        expected_plan=(
            "MERGE     config/dev-dependencies.txt",
            "CONFLICT  .pre-commit-config.yaml",
            "ADD       .github/workflows/verify.yml",
        ),
        preserved_paths=(
            "README.md",
            "pyproject.toml",
            ".github/workflows/ci.yml",
            "src/acme_catalog/__init__.py",
            "tests/test_catalog.py",
        ),
        backup_paths=(".pre-commit-config.yaml",),
        merged_fragments=(
            (
                "config/dev-dependencies.txt",
                ("pytest>=8.0", "ruff>=0.12", "agent-maintainer[core]"),
            ),
        ),
    ),
    ExistingApplicationCase(
        name="flat-service",
        track="agent",
        python_path=".",
        expected_plan=(
            "MERGE     config/dev-dependencies.txt",
            "ADD       .pre-commit-config.yaml",
            "CONFLICT  .github/workflows/verify.yml",
            "SKIP      AGENTS.md",
            "MERGE     .codex/config.toml",
            "MERGE     .claude/settings.json",
        ),
        preserved_paths=(
            "AGENTS.md",
            "README.md",
            "pyproject.toml",
            "requirements.txt",
            "billing_service/__init__.py",
            "tests/test_invoice.py",
        ),
        backup_paths=(".github/workflows/verify.yml",),
        merged_fragments=(
            (
                "config/dev-dependencies.txt",
                ("pytest>=8.0", "agent-maintainer[core]"),
            ),
            (
                ".codex/config.toml",
                ("team-tool", "agent-maintainer:codex-hooks"),
            ),
            (
                ".claude/settings.json",
                ("third-party-stop", ".claude/hooks/stop.py"),
            ),
        ),
    ),
    ExistingApplicationCase(
        name="uv-web-app",
        track="hardening",
        python_path="src",
        expected_plan=(
            "MERGE     config/dev-dependencies.txt",
            "CONFLICT  .pre-commit-config.yaml",
            "ADD       .github/workflows/verify.yml",
            "SKIP      AGENTS.md",
            "MERGE     package.json",
        ),
        preserved_paths=(
            "AGENTS.md",
            "README.md",
            "pyproject.toml",
            "uv.lock",
            ".github/workflows/ci.yml",
            "src/web_status/__init__.py",
            "tests/test_status.py",
        ),
        backup_paths=(".pre-commit-config.yaml",),
        merged_fragments=(
            (
                "config/dev-dependencies.txt",
                ("pytest>=8.0", "agent-maintainer[core]"),
            ),
            (
                "package.json",
                (
                    '"test": "pytest -q"',
                    '"vitest": "2.1.9"',
                    '"@taplo/cli": "0.7.0"',
                    '"markdownlint-cli2": "0.22.1"',
                ),
            ),
        ),
    ),
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_existing_application_onboarding_is_transactional(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: ExistingApplicationCase,
) -> None:
    """Three representative existing apps preserve user work and rerun cleanly."""

    repository = tmp_path / case.name
    shutil.copytree(FIXTURE_ROOT / case.name, repository)
    _materialize_python_templates(repository)
    _commit_fixture(repository)
    baseline = _worktree_payloads(repository)
    command = ["--target", str(repository), "--track", case.track]

    assert initializer.main([*command, "--dry-run"]) == 0
    preview = capsys.readouterr().out
    for expected in case.expected_plan:
        assert expected in preview
    assert _worktree_payloads(repository) == baseline
    assert _git(repository, "status", "--porcelain").stdout == ""

    assert initializer.main(command) == 1
    capsys.readouterr()
    assert _worktree_payloads(repository) == baseline
    assert _git(repository, "status", "--porcelain").stdout == ""

    assert initializer.main([*command, "--force"]) == 0
    capsys.readouterr()
    _assert_preserved_files(repository, baseline, case)
    _assert_backups(repository, baseline, case)
    _assert_merged_content(repository, case)
    _assert_semantic_merges(repository, case)
    _run_application_tests(repository, case)

    applied = _worktree_payloads(repository)
    transactions = _transaction_names(repository)
    status = _git(repository, "status", "--porcelain").stdout

    assert initializer.main([*command, "--force"]) == 0
    capsys.readouterr()
    assert _worktree_payloads(repository) == applied
    assert _transaction_names(repository) == transactions
    assert _git(repository, "status", "--porcelain").stdout == status


def test_existing_application_fixture_corpus_has_three_distinct_shapes() -> None:
    """The release contract cannot regress to generated single-shape fixtures."""

    fixture_names = tuple(sorted(path.name for path in FIXTURE_ROOT.iterdir() if path.is_dir()))

    assert fixture_names == tuple(sorted(case.name for case in CASES))
    assert len({case.python_path for case in CASES}) == EXPECTED_PYTHON_LAYOUT_COUNT
    assert {case.track for case in CASES} == {"agent", "core", "hardening"}


def _commit_fixture(repository: Path) -> None:
    _git(repository, "init", "-b", "main")
    _git(repository, "add", "--all")
    _git(
        repository,
        "-c",
        "user.name=Agent Maintainer",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "test: seed existing application",
    )


def _materialize_python_templates(repository: Path) -> None:
    for template in repository.rglob("*.py.fixture"):
        template.replace(template.with_suffix(""))


def _assert_preserved_files(
    repository: Path,
    baseline: dict[str, bytes],
    case: ExistingApplicationCase,
) -> None:
    for relative_path in case.preserved_paths:
        assert (repository / relative_path).read_bytes() == baseline[relative_path]


def _assert_backups(
    repository: Path,
    baseline: dict[str, bytes],
    case: ExistingApplicationCase,
) -> None:
    backup_root = transaction.backup_root(repository)
    for relative_path in case.backup_paths:
        matches = tuple(backup_root.glob(f"*/files/{relative_path}"))
        assert len(matches) == 1
        assert matches[0].read_bytes() == baseline[relative_path]


def _assert_merged_content(repository: Path, case: ExistingApplicationCase) -> None:
    for relative_path, fragments in case.merged_fragments:
        content = (repository / relative_path).read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in content


def _assert_semantic_merges(repository: Path, case: ExistingApplicationCase) -> None:
    codex_config = repository / ".codex/config.toml"
    claude_settings = repository / ".claude/settings.json"
    package_json = repository / "package.json"
    if codex_config.exists():
        _assert_codex_config(codex_config, preserve_team_tool=case.name == "flat-service")
    if claude_settings.exists():
        _assert_claude_settings(
            claude_settings,
            preserve_third_party=case.name == "flat-service",
        )
    if package_json.exists():
        _assert_package_json(package_json)


def _assert_codex_config(path: Path, *, preserve_team_tool: bool) -> None:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    assert payload["features"]["hooks"] is True
    hooks = payload["hooks"]
    post_commands = _hook_commands(hooks["PostToolUse"])
    stop_commands = _hook_commands(hooks["Stop"])
    assert any(
        command.endswith('/.codex/hooks/post_edit_fast_gate.py"') for command in post_commands
    )
    assert any(command.endswith('/.codex/hooks/post_pr_wait.py"') for command in post_commands)
    assert any(command.endswith('/.codex/hooks/stop_full_verify.py"') for command in stop_commands)
    if preserve_team_tool:
        assert payload["mcp_servers"]["team_tool"] == {
            "args": ["serve"],
            "command": "team-tool",
        }


def _assert_claude_settings(path: Path, *, preserve_third_party: bool) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    hooks = payload["hooks"]
    post_commands = _hook_commands(hooks["PostToolUse"])
    stop_commands = _hook_commands(hooks["Stop"])
    subagent_commands = _hook_commands(hooks["SubagentStop"])
    assert any(command.endswith('/.claude/hooks/post_tool_use.py"') for command in post_commands)
    assert any(command.endswith('/.claude/hooks/post_pr_wait.py"') for command in post_commands)
    assert any(command.endswith('/.claude/hooks/stop.py"') for command in stop_commands)
    assert any(
        command.endswith('/.claude/hooks/subagent_stop.py"') for command in subagent_commands
    )
    if preserve_third_party:
        assert payload["theme"] == "dark"
        assert "third-party-stop" in stop_commands


def _assert_package_json(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["name"] == "uv-web-app-assets"
    assert payload["scripts"] == {"test": "pytest -q"}
    assert payload["devDependencies"] == {
        "@taplo/cli": "0.7.0",
        "markdownlint-cli2": "0.22.1",
        "vitest": "2.1.9",
    }


def _hook_commands(entries: object) -> set[str]:
    assert isinstance(entries, list)
    commands: set[str] = set()
    for entry in entries:
        assert isinstance(entry, dict)
        hooks = entry.get("hooks")
        assert isinstance(hooks, list)
        for hook in hooks:
            assert isinstance(hook, dict)
            command = hook.get("command")
            assert isinstance(command, str)
            commands.add(command)
    return commands


def _run_application_tests(repository: Path, case: ExistingApplicationCase) -> None:
    environment = dict(os.environ)
    environment.pop("COVERAGE_FILE", None)
    environment.pop("COVERAGE_PROCESS_START", None)
    environment.pop("PYTEST_ADDOPTS", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(repository / case.python_path)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _worktree_payloads(repository: Path) -> dict[str, bytes]:
    return {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repository).parts
    }


def _transaction_names(repository: Path) -> tuple[str, ...]:
    backup_root = transaction.backup_root(repository)
    return tuple(sorted(path.name for path in backup_root.iterdir()))


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
