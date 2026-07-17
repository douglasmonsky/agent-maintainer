"""Tests versioned provider-neutral per-path file ceilings."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - isolated local Git fixtures
from pathlib import Path

import pytest

from agent_maintainer.assess import cli
from agent_maintainer.assess.file_baseline_state import (
    FileCeilingObservation,
    compare_baseline,
    create_baseline,
)
from agent_maintainer.assess.file_baselines import build_file_baseline_report
from agent_maintainer.config import loader

BASELINE_PATH = ".agent-maintainer/file-baselines.json"
JAVA_LEGACY = "src/main/java/example/Legacy.java"
JAVA_NEW = "src/main/java/example/NewFile.java"
PYTHON_LEGACY = "src/example/legacy.py"
MAX_PHYSICAL = 5
MAX_NONBLANK = 4
ENCODING = "utf-8"
EXPECTED_BASELINE_ENTRIES = 2


# docsync:evidence.start evidence.file_baselines.provider_neutral
def test_physical_and_nonblank_defaults_can_be_enabled_independently() -> None:
    """A disabled physical ceiling does not invalidate a nonblank-only group."""
    observation = FileCeilingObservation(
        "docs",
        "docs/guide.md",
        physical=7,
        nonblank=6,
        default_physical=0,
        default_nonblank=4,
    )

    assert observation.default_physical == 0
    assert observation.default_nonblank == MAX_NONBLANK

    stored = create_baseline((observation,), source_commit="a" * 40)
    assert stored.entries[0].physical_ceiling == 0
    current = FileCeilingObservation(
        "docs",
        "docs/guide.md",
        physical=8,
        nonblank=6,
        default_physical=0,
        default_nonblank=4,
    )

    assert compare_baseline(stored, (current,)).passed is True


def test_create_and_inspect_are_deterministic_and_provider_neutral(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One versioned lifecycle records Java and Python without language branches."""
    repo = initialized_repo(
        tmp_path,
        {
            JAVA_LEGACY: lines(7),
            PYTHON_LEGACY: lines(6),
        },
    )

    dry_status = cli.main(file_command("create", repo, "--dry-run"))
    dry_output = capsys.readouterr().out
    payload = json.loads(dry_output)

    assert dry_status == 0
    assert payload["version"] == 1
    assert [(entry["group"], entry["path"]) for entry in payload["entries"]] == [
        ("java", JAVA_LEGACY),
        ("python", PYTHON_LEGACY),
    ]
    assert not (repo / BASELINE_PATH).exists()

    assert cli.main(file_command("create", repo)) == 0
    written_output = capsys.readouterr().out
    baseline_path = repo / BASELINE_PATH
    assert baseline_path.read_text(encoding=ENCODING) == dry_output
    assert written_output == dry_output
    before_inspect = baseline_path.read_bytes()

    assert cli.main(file_command("inspect", repo, "--json")) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["entry_count"] == EXPECTED_BASELINE_ENTRIES
    assert summary["group_count"] == EXPECTED_BASELINE_ENTRIES
    assert baseline_path.read_bytes() == before_inspect


def test_established_floors_block_regressions_and_new_file_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored oversized files may hold steady while growth and new debt fail."""
    repo = initialized_repo(
        tmp_path,
        {
            JAVA_LEGACY: lines(7),
            PYTHON_LEGACY: lines(7),
        },
    )
    create_and_commit_baseline(repo)
    config = loader.load_config(repo)
    monkeypatch.chdir(repo)

    steady = build_file_baseline_report(repo, config, base_ref="HEAD", staged=False)
    assert steady.passed is True
    assert not any(finding.path in {JAVA_LEGACY, PYTHON_LEGACY} for finding in steady.findings)

    write(repo / JAVA_LEGACY, lines(8))
    write(repo / JAVA_NEW, lines(6))
    write(repo / PYTHON_LEGACY, lines(6))
    report = build_file_baseline_report(repo, config, base_ref="HEAD", staged=False)

    blocking_paths = {finding.path for finding in report.findings if finding.blocking}
    advisory_paths = {finding.path for finding in report.findings if not finding.blocking}
    assert report.passed is False
    assert blocking_paths == {JAVA_LEGACY, JAVA_NEW}
    assert PYTHON_LEGACY in advisory_paths
    assert any("baseline ceiling" in finding.message for finding in report.findings)
    assert any("new oversized file" in finding.message for finding in report.findings)
    assert any("eligible for prune" in finding.message for finding in report.findings)


def test_blocking_mode_returns_nonzero_without_mutating_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The report command blocks regressions but never rewrites its baseline."""
    repo = initialized_repo(tmp_path, {JAVA_LEGACY: lines(7)})
    create_and_commit_baseline(repo)
    capsys.readouterr()
    baseline_path = repo / BASELINE_PATH
    before = baseline_path.read_bytes()
    write(repo / JAVA_LEGACY, lines(8))

    status = cli.main(["file-baselines", "--target", str(repo), "--base-ref", "HEAD", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert status != 0
    assert payload["passed"] is False
    assert baseline_path.read_bytes() == before


def test_rename_is_new_debt_and_leaves_old_entry_prunable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rename cannot transfer an oversized allowance to an unreviewed path."""
    repo = initialized_repo(tmp_path, {JAVA_LEGACY: lines(7)})
    create_and_commit_baseline(repo)
    renamed = "src/main/java/example/Renamed.java"
    git(repo, "mv", JAVA_LEGACY, renamed)
    config = loader.load_config(repo)
    monkeypatch.chdir(repo)

    report = build_file_baseline_report(repo, config, base_ref="HEAD", staged=False)

    assert report.passed is False
    assert any(finding.path == renamed and finding.blocking for finding in report.findings)
    assert any(
        finding.path == JAVA_LEGACY and finding.kind == "baseline-removed"
        for finding in report.findings
    )


def test_prune_only_lowers_improved_entries_and_removes_absent_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit prune lowers one ceiling and removes another deterministically."""
    repo = initialized_repo(
        tmp_path,
        {
            JAVA_LEGACY: lines(7),
            PYTHON_LEGACY: lines(7),
        },
    )
    create_and_commit_baseline(repo)
    capsys.readouterr()
    write(repo / JAVA_LEGACY, lines(6))
    (repo / PYTHON_LEGACY).unlink()
    git(repo, "add", "--all")
    git(repo, "commit", "-m", "improve file ceilings")
    baseline_path = repo / BASELINE_PATH
    before = baseline_path.read_bytes()

    assert cli.main(file_command("prune", repo, "--dry-run")) == 0
    dry_output = capsys.readouterr().out
    dry_payload = json.loads(dry_output)
    assert baseline_path.read_bytes() == before
    assert [(entry["path"], entry["physical_ceiling"]) for entry in dry_payload["entries"]] == [
        (JAVA_LEGACY, 6)
    ]

    assert cli.main(file_command("prune", repo)) == 0
    written_output = capsys.readouterr().out
    assert written_output == dry_output
    assert baseline_path.read_text(encoding=ENCODING) == dry_output


def test_prune_rejects_regressions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Prune cannot admit a larger ceiling or a newly oversized file."""
    repo = initialized_repo(tmp_path, {JAVA_LEGACY: lines(7)})
    create_and_commit_baseline(repo)
    write(repo / JAVA_LEGACY, lines(8))
    git(repo, "add", JAVA_LEGACY)
    git(repo, "commit", "-m", "regress file ceiling")
    baseline_path = repo / BASELINE_PATH
    before = baseline_path.read_bytes()

    status = cli.main(file_command("prune", repo))

    assert status != 0
    assert "new or regressed" in capsys.readouterr().err
    assert baseline_path.read_bytes() == before


# docsync:evidence.end evidence.file_baselines.provider_neutral


def initialized_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a clean repository with Java and Python file-ceiling groups."""
    repo = tmp_path / "repo"
    repo.mkdir()
    write(repo / "pyproject.toml", configuration_text())
    for relative, content in files.items():
        write(repo / relative, content)
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    git(repo, "add", "--all")
    git(repo, "commit", "-m", "initial")
    return repo


def configuration_text() -> str:
    """Return blocking provider-neutral config for two ecosystems."""
    return f"""
[tool.agent_maintainer.file_baselines]
enabled = true
mode = "blocking"
baseline = "{BASELINE_PATH}"

[tool.agent_maintainer.file_baselines.groups.java]
include = ["src/main/java/**/*.java"]
role = "source"
max_physical_lines = {MAX_PHYSICAL}
max_nonblank_lines = {MAX_NONBLANK}

[tool.agent_maintainer.file_baselines.groups.python]
include = ["src/**/*.py"]
exclude = ["src/main/java/**"]
role = "source"
max_physical_lines = {MAX_PHYSICAL}
max_nonblank_lines = {MAX_NONBLANK}
""".strip()


def create_and_commit_baseline(repo: Path) -> None:
    """Create and review the current explicit file ceiling baseline."""
    assert cli.main(file_command("create", repo)) == 0
    git(repo, "add", BASELINE_PATH)
    git(repo, "commit", "-m", "record file ceiling baseline")


def file_command(operation: str, repo: Path, *extra: str) -> list[str]:
    """Return one file-baseline lifecycle command."""
    return ["file-baselines", operation, "--target", str(repo), *extra]


def lines(count: int) -> str:
    """Return a file with exactly count physical and nonblank lines."""
    return "".join(f"line {index}\n" for index in range(count))


def write(path: Path, content: str) -> None:
    """Write one fixture file beneath created parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=ENCODING)


def git(repo: Path, *args: str) -> str:
    """Run one deterministic local Git fixture command."""
    completed = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
