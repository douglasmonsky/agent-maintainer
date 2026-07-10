"""Tests transactional managed-hook filesystem mutation."""

import json
from pathlib import Path

import pytest

from agent_maintainer.hooks import manager, mutations

EXPECTED_BACKUP_COUNT = 2


def test_install_second_run_is_byte_noop_without_backup(tmp_path: Path) -> None:
    """A current installation creates no new transaction or file changes."""

    options = manager.InstallOptions(target=tmp_path, client=manager.ALL_CLIENTS)
    assert manager.install_hooks(options) == 0
    before = _managed_payloads(tmp_path)
    transactions = _transaction_roots(tmp_path)

    assert manager.install_hooks(options) == 0

    assert _managed_payloads(tmp_path) == before
    assert _transaction_roots(tmp_path) == transactions


def test_dry_run_never_creates_backup_or_destination(tmp_path: Path) -> None:
    """Preview reports writes without creating destinations or rollback data."""

    assert (
        manager.install_hooks(
            manager.InstallOptions(
                target=tmp_path,
                client=manager.ALL_CLIENTS,
                dry_run=True,
            )
        )
        == 0
    )

    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / mutations.BACKUP_ROOT).exists()


def test_rapid_replacements_create_collision_proof_backups(tmp_path: Path) -> None:
    """Separate replacements cannot reuse a timestamp-based backup path."""

    path = tmp_path / "hook.py"
    path.write_text("first", encoding="utf-8")
    options = manager.InstallOptions(target=tmp_path, client=manager.CODEX_CLIENT)

    manager.write_plan(manager.PlannedWrite(path, "second", "hook"), options)
    manager.write_plan(manager.PlannedWrite(path, "third", "hook"), options)

    backups = sorted((tmp_path / mutations.BACKUP_ROOT).glob("*/files/hook.py"))
    assert len(backups) == EXPECTED_BACKUP_COUNT
    assert {path.read_text(encoding="utf-8") for path in backups} == {"first", "second"}


def test_transaction_failure_restores_every_prior_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later atomic-write failure restores earlier writes from backups."""

    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("first-old", encoding="utf-8")
    second.write_text("second-old", encoding="utf-8")
    prepared = (
        mutations.prepare_write(
            manager.PlannedWrite(first, "first-new", "first"),
            "first-new",
        ),
        mutations.prepare_write(
            manager.PlannedWrite(second, "second-new", "second"),
            "second-new",
        ),
    )
    real_atomic_write = mutations.atomic_write_text

    def fail_second(path: Path, content: str) -> None:
        if path == second:
            raise OSError("synthetic interruption")
        real_atomic_write(path, content)

    monkeypatch.setattr(mutations, "atomic_write_text", fail_second)

    with pytest.raises(mutations.HookMutationError, match="rolled back"):
        mutations.apply_transaction(prepared, ownership_root=tmp_path)

    assert first.read_text(encoding="utf-8") == "first-old"
    assert second.read_text(encoding="utf-8") == "second-old"


def test_transaction_failure_restores_prior_deletion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later write failure restores an earlier transactionally removed file."""

    removed = tmp_path / "removed.py"
    failing = tmp_path / "failing.py"
    removed.write_text("managed", encoding="utf-8")
    failing.write_text("old", encoding="utf-8")
    prepared = (
        mutations.prepare_delete(manager.PlannedWrite(removed, "", "removed")),
        mutations.prepare_write(manager.PlannedWrite(failing, "new", "failing"), "new"),
    )
    monkeypatch.setattr(
        mutations,
        "atomic_write_text",
        lambda _path, _content: (_ for _ in ()).throw(OSError("synthetic interruption")),
    )

    with pytest.raises(mutations.HookMutationError, match="rolled back"):
        mutations.apply_transaction(prepared, ownership_root=tmp_path)

    assert removed.read_text(encoding="utf-8") == "managed"
    assert failing.read_text(encoding="utf-8") == "old"


def test_rollback_manifest_records_restore_and_remove_actions(tmp_path: Path) -> None:
    """Transaction metadata gives explicit recovery actions without file content."""

    existing = tmp_path / "existing.py"
    created = tmp_path / "created.py"
    existing.write_text("old", encoding="utf-8")
    prepared = (
        mutations.prepare_write(manager.PlannedWrite(existing, "new", "existing"), "new"),
        mutations.prepare_write(manager.PlannedWrite(created, "new", "created"), "new"),
    )

    result = mutations.apply_transaction(prepared, ownership_root=tmp_path)

    assert result.rollback_manifest is not None
    payload = json.loads(result.rollback_manifest.read_text(encoding="utf-8"))
    assert payload["files"] == [
        {"action": "restore", "backup": "files/existing.py", "path": "existing.py"},
        {"action": "remove", "backup": None, "path": "created.py"},
    ]
    assert all("content" not in entry for entry in payload["files"])


def test_invalid_config_fails_before_any_client_write(tmp_path: Path) -> None:
    """A late render conflict is detected before earlier client files mutate."""

    settings = tmp_path / ".claude/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{", encoding="utf-8")

    assert (
        manager.install_hooks(manager.InstallOptions(target=tmp_path, client=manager.ALL_CLIENTS))
        == 1
    )

    assert settings.read_text(encoding="utf-8") == "{"
    assert not (tmp_path / ".codex").exists()
    assert not (tmp_path / mutations.BACKUP_ROOT).exists()


def test_force_replaces_invalid_config_after_backup(tmp_path: Path) -> None:
    """Force resolves invalid managed JSON without waiving backup policy."""

    settings = tmp_path / ".claude/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{", encoding="utf-8")

    assert (
        manager.install_hooks(
            manager.InstallOptions(
                target=tmp_path,
                client=manager.CLAUDE_CODE_CLIENT,
                force=True,
            )
        )
        == 0
    )

    json.loads(settings.read_text(encoding="utf-8"))
    backups = list((tmp_path / mutations.BACKUP_ROOT).glob("*/files/.claude/settings.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{"


def test_git_private_backup_root_supports_linked_worktree_marker(tmp_path: Path) -> None:
    """Repository recovery follows a linked worktree's real Git directory."""

    repo = tmp_path / "repo"
    git_directory = tmp_path / "git-data"
    repo.mkdir()
    git_directory.mkdir()
    (repo / ".git").write_text("gitdir: ../git-data\n", encoding="utf-8")

    assert mutations.backup_root(repo, git_private=True) == (
        git_directory / mutations.GIT_BACKUP_ROOT
    )


def _transaction_roots(root: Path) -> tuple[str, ...]:
    backup_root = root / mutations.BACKUP_ROOT
    return (
        tuple(sorted(path.name for path in backup_root.iterdir())) if backup_root.exists() else ()
    )


def _managed_payloads(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for parent in (root / ".codex", root / ".claude")
        if parent.exists()
        for path in parent.rglob("*")
        if path.is_file()
    }
