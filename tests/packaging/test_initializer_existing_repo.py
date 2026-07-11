"""Tests transactional initializer behavior in existing repositories."""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.core.scaffold import initializer, planning, templates, transaction

USER_FILE_MODE = 0o600


def test_existing_repo_dry_run_classifies_without_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Preview reports add/unchanged/merge/conflict/skip without force."""

    _existing_agent_repo(tmp_path)
    workflow = tmp_path / ".github/workflows/verify.yml"
    workflow.chmod(USER_FILE_MODE)
    before = _tree_payloads(tmp_path)

    assert initializer.main(["--target", str(tmp_path), "--track", "agent", "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "MERGE     config/dev-dependencies.txt" in output
    assert "UNCHANGED .pre-commit-config.yaml" in output
    assert "CONFLICT  .github/workflows/verify.yml" in output
    assert "SKIP      AGENTS.md" in output
    assert "ADD       .codex/config.toml" in output
    assert "dry-run: no files written" in output
    assert _tree_payloads(tmp_path) == before
    assert not (tmp_path / transaction.BACKUP_ROOT).exists()


def test_conflict_refuses_entire_apply_without_force(tmp_path: Path) -> None:
    """A conflict stops additions and merges before the first write."""

    _existing_agent_repo(tmp_path)
    before = _tree_payloads(tmp_path)

    assert initializer.main(["--target", str(tmp_path), "--track", "agent"]) == 1

    assert _tree_payloads(tmp_path) == before
    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / transaction.BACKUP_ROOT).exists()


def test_force_backs_up_conflict_and_preserves_user_files(tmp_path: Path) -> None:
    """Forced apply merges supported files, skips AGENTS, and backs conflicts."""

    _existing_agent_repo(tmp_path)
    workflow = tmp_path / ".github/workflows/verify.yml"
    workflow.chmod(USER_FILE_MODE)
    claude = tmp_path / ".claude/settings.json"
    claude.parent.mkdir(parents=True)
    claude.write_text(
        json.dumps({"hooks": {"Stop": [_third_party_entry()]}, "theme": "dark"}),
        encoding="utf-8",
    )

    assert initializer.main(["--target", str(tmp_path), "--track", "agent", "--force"]) == 0

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "user guidance\n"
    dependencies = (tmp_path / "config/dev-dependencies.txt").read_text(encoding="utf-8")
    assert dependencies == "pytest\nagent-maintainer[core]\n"
    settings = json.loads(claude.read_text(encoding="utf-8"))
    assert settings["theme"] == "dark"
    assert settings["hooks"]["Stop"][0] == _third_party_entry()
    workflow_backups = list(
        (tmp_path / transaction.BACKUP_ROOT).glob("*/files/.github/workflows/verify.yml")
    )
    assert len(workflow_backups) == 1
    assert workflow_backups[0].read_text(encoding="utf-8") == "user workflow\n"
    assert stat.S_IMODE(workflow.stat().st_mode) == USER_FILE_MODE


def test_second_forced_apply_is_byte_noop(tmp_path: Path) -> None:
    """A rerun changes no managed bytes and creates no recovery transaction."""

    _existing_agent_repo(tmp_path)
    command = ["--target", str(tmp_path), "--track", "agent", "--force"]
    assert initializer.main(command) == 0
    before = _tree_payloads(tmp_path, include_backups=False)
    transactions = _transaction_names(tmp_path)

    assert initializer.main(command) == 0

    assert _tree_payloads(tmp_path, include_backups=False) == before
    assert _transaction_names(tmp_path) == transactions


def test_interrupted_initializer_rolls_back_prior_additions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later atomic write failure removes all earlier new destinations."""

    failing_path = tmp_path / ".pre-commit-config.yaml"
    real_atomic_write = transaction.atomic_write_text

    def fail_pre_commit(path: Path, content: str) -> None:
        if path == failing_path:
            raise OSError("synthetic interruption")
        real_atomic_write(path, content)

    monkeypatch.setattr(transaction, "atomic_write_text", fail_pre_commit)

    assert initializer.main(["--target", str(tmp_path)]) == 1

    assert not (tmp_path / "config/pyproject.agent-maintainer.toml").exists()
    assert not (tmp_path / "config/dev-dependencies.txt").exists()
    assert not failing_path.exists()


def test_hardening_package_merge_preserves_existing_metadata(tmp_path: Path) -> None:
    """Compatible package metadata gains tooling dependencies without replacement."""

    package = tmp_path / "package.json"
    package.write_text(
        json.dumps({"name": "existing", "scripts": {"test": "vitest"}}),
        encoding="utf-8",
    )
    files = initializer.files_for_track("hardening")
    plan = planning.build_plan(tmp_path, files)
    package_item = next(item for item in plan if item.starter.path == "package.json")

    assert package_item.action == planning.InitAction.MERGE
    assert package_item.content is not None
    merged = json.loads(package_item.content)
    assert merged["name"] == "existing"
    assert merged["scripts"] == {"test": "vitest"}
    assert merged["engines"] == {"node": ">=22"}
    assert "markdownlint-cli2" in merged["devDependencies"]


def test_hardening_package_merge_refuses_incompatible_node_engine(tmp_path: Path) -> None:
    """An explicit incompatible Node contract is reviewed as a conflict."""

    package = tmp_path / "package.json"
    package.write_text(
        json.dumps({"name": "existing", "engines": {"node": ">=20"}}),
        encoding="utf-8",
    )
    files = initializer.files_for_track("hardening")
    plan = planning.build_plan(tmp_path, files)
    package_item = next(item for item in plan if item.starter.path == "package.json")

    assert package_item.action == planning.InitAction.CONFLICT
    assert package_item.reason == "existing content requires explicit replacement"


def test_hardening_package_merge_refuses_dependency_version_conflict(tmp_path: Path) -> None:
    """An existing managed dependency version remains an explicit conflict."""

    package = tmp_path / "package.json"
    package.write_text(
        json.dumps(
            {
                "name": "existing",
                "devDependencies": {"markdownlint-cli2": "0.22.1"},
            }
        ),
        encoding="utf-8",
    )
    files = initializer.files_for_track("hardening")
    plan = planning.build_plan(tmp_path, files)
    package_item = next(item for item in plan if item.starter.path == "package.json")

    assert package_item.action == planning.InitAction.CONFLICT
    assert package_item.reason == "existing content requires explicit replacement"


def test_hardening_package_merge_preserves_other_engine_contracts(tmp_path: Path) -> None:
    """Adding the required Node engine preserves unrelated engine metadata."""

    package = tmp_path / "package.json"
    package.write_text(
        json.dumps({"name": "existing", "engines": {"npm": ">=10"}}),
        encoding="utf-8",
    )
    files = initializer.files_for_track("hardening")
    plan = planning.build_plan(tmp_path, files)
    package_item = next(item for item in plan if item.starter.path == "package.json")

    assert package_item.action == planning.InitAction.MERGE
    assert package_item.content is not None
    merged = json.loads(package_item.content)
    assert merged["engines"] == {"node": ">=22", "npm": ">=10"}


def test_clean_clone_initializer_twice_keeps_git_status_clean(tmp_path: Path) -> None:
    """A generated adoption is unchanged on first and second clean-clone apply."""

    seed = tmp_path / "seed"
    clone = tmp_path / "clone"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    assert initializer.main(["--target", str(seed), "--track", "agent"]) == 0
    _git(seed, "add", "--all")
    _git(
        seed,
        "-c",
        "user.name=Agent Maintainer",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "seed",
    )
    _git(tmp_path, "clone", str(seed), str(clone))
    command = ["--target", str(clone), "--track", "agent"]

    assert initializer.main(command) == 0
    assert _git(clone, "status", "--porcelain").stdout == ""
    assert initializer.main(command) == 0
    assert _git(clone, "status", "--porcelain").stdout == ""
    assert not transaction.backup_root(clone).exists()


def test_initializer_backup_root_supports_linked_worktree_marker(tmp_path: Path) -> None:
    """Initializer recovery follows a linked worktree's real Git directory."""

    repo = tmp_path / "repo"
    git_directory = tmp_path / "git-data"
    repo.mkdir()
    git_directory.mkdir()
    (repo / ".git").write_text("gitdir: ../git-data\n", encoding="utf-8")

    assert transaction.backup_root(repo) == git_directory / transaction.GIT_BACKUP_ROOT


def _existing_agent_repo(root: Path) -> None:
    dependency = root / "config/dev-dependencies.txt"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("pytest\n", encoding="utf-8")
    (root / ".pre-commit-config.yaml").write_text(
        templates.PRE_COMMIT_CONFIG,
        encoding="utf-8",
    )
    workflow = root / ".github/workflows/verify.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("user workflow\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("user guidance\n", encoding="utf-8")


def _third_party_entry() -> dict[str, object]:
    return {"hooks": [{"type": "command", "command": "third-party"}]}


def _transaction_names(root: Path) -> tuple[str, ...]:
    backup_root = transaction.backup_root(root)
    return (
        tuple(sorted(path.name for path in backup_root.iterdir())) if backup_root.exists() else ()
    )


def _tree_payloads(root: Path, *, include_backups: bool = True) -> dict[str, bytes]:
    backup_root = transaction.backup_root(root)
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and (include_backups or backup_root not in path.parents)
    }


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
