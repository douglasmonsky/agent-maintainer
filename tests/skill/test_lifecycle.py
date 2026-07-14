"""Tests for ownership-safe personal skill installation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from agent_maintainer.skill import lifecycle, resources
from agent_maintainer.skill.models import SkillBundle, SkillFile, SkillState

CLIENTS = ("codex", "claude-code")


def test_install_status_and_uninstall_both_clients(tmp_path: Path) -> None:
    """Both clients receive and safely remove the same portable bundle."""

    assert tuple(lifecycle.status(tmp_path, client).state for client in CLIENTS) == (
        SkillState.MISSING,
        SkillState.MISSING,
    )

    installed = lifecycle.install(tmp_path, CLIENTS)

    assert all(item.state is SkillState.CURRENT for item in installed)
    for client in CLIENTS:
        destination = lifecycle.client_destination(tmp_path, client)
        assert (destination / "SKILL.md").is_file()
        assert (destination / "agents/openai.yaml").is_file()
        assert (destination / lifecycle.MANIFEST_NAME).is_file()
    assert lifecycle.install(tmp_path, CLIENTS) == installed

    removed = lifecycle.uninstall(tmp_path, CLIENTS)

    assert all(item.state is SkillState.MISSING for item in removed)
    assert all(not lifecycle.client_destination(tmp_path, client).exists() for client in CLIENTS)


def test_modified_managed_file_blocks_update_and_uninstall(tmp_path: Path) -> None:
    """User changes never become implicitly owned or deleted."""

    lifecycle.install(tmp_path, ("codex",))
    skill = lifecycle.client_destination(tmp_path, "codex") / "SKILL.md"
    skill.write_text("user content\n", encoding="utf-8")

    assert lifecycle.status(tmp_path, "codex").state is SkillState.LOCALLY_MODIFIED
    with pytest.raises(lifecycle.SkillOwnershipError, match="locally modified"):
        lifecycle.install(tmp_path, ("codex",))
    with pytest.raises(lifecycle.SkillOwnershipError, match="locally modified"):
        lifecycle.uninstall(tmp_path, ("codex",))
    assert skill.read_text(encoding="utf-8") == "user content\n"


def test_stale_owned_files_update_and_preserve_unrelated_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new bundle replaces owned files without disturbing neighbors."""

    lifecycle.install(tmp_path, ("claude-code",))
    destination = lifecycle.client_destination(tmp_path, "claude-code")
    unrelated = destination / "notes.txt"
    unrelated.write_text("keep\n", encoding="utf-8")
    changed = _changed_bundle(resources.load_bundle())
    monkeypatch.setattr(lifecycle.resources, "load_bundle", lambda: changed)

    assert lifecycle.status(tmp_path, "claude-code").state is SkillState.STALE
    updated = lifecycle.install(tmp_path, ("claude-code",))[0]

    assert updated.state is SkillState.CURRENT
    assert updated.package_version == changed.package_version
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert (destination / "SKILL.md").read_text(encoding="utf-8").endswith("\n# changed\n")


def test_uninstall_preserves_unrelated_content(tmp_path: Path) -> None:
    """Removing a managed skill leaves unrelated files in its directory."""

    lifecycle.install(tmp_path, ("codex",))
    destination = lifecycle.client_destination(tmp_path, "codex")
    unrelated = destination / "notes.txt"
    unrelated.write_text("keep\n", encoding="utf-8")

    result = lifecycle.uninstall(tmp_path, ("codex",))[0]

    assert result.state is SkillState.MISSING
    assert destination.is_dir()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert not (destination / "SKILL.md").exists()
    assert not (destination / "agents").exists()
    assert not (destination / lifecycle.MANIFEST_NAME).exists()


def test_existing_unowned_destination_is_never_adopted(tmp_path: Path) -> None:
    """An existing same-name directory requires explicit human resolution."""

    destination = lifecycle.client_destination(tmp_path, "codex")
    destination.mkdir(parents=True)
    existing = destination / "notes.txt"
    existing.write_text("mine\n", encoding="utf-8")

    assert lifecycle.status(tmp_path, "codex").state is SkillState.LOCALLY_MODIFIED
    with pytest.raises(lifecycle.SkillOwnershipError, match="ownership manifest"):
        lifecycle.install(tmp_path, ("codex",))
    assert existing.read_text(encoding="utf-8") == "mine\n"


@pytest.mark.parametrize("manifest_content", ("not json\n", "{}\n"))
def test_invalid_manifest_blocks_mutation(tmp_path: Path, manifest_content: str) -> None:
    """Malformed or incomplete ownership data fails closed."""

    lifecycle.install(tmp_path, ("codex",))
    destination = lifecycle.client_destination(tmp_path, "codex")
    (destination / lifecycle.MANIFEST_NAME).write_text(manifest_content, encoding="utf-8")

    assert lifecycle.status(tmp_path, "codex").state is SkillState.LOCALLY_MODIFIED
    with pytest.raises(lifecycle.SkillOwnershipError):
        lifecycle.uninstall(tmp_path, ("codex",))


def test_missing_managed_file_blocks_mutation(tmp_path: Path) -> None:
    """A partially removed installation is not treated as owned."""

    lifecycle.install(tmp_path, ("codex",))
    destination = lifecycle.client_destination(tmp_path, "codex")
    (destination / "SKILL.md").unlink()

    status = lifecycle.status(tmp_path, "codex")

    assert status.state is SkillState.LOCALLY_MODIFIED
    assert "missing managed file" in status.detail


def test_manifest_for_another_client_blocks_mutation(tmp_path: Path) -> None:
    """Client identity is part of the ownership boundary."""

    lifecycle.install(tmp_path, ("codex",))
    destination = lifecycle.client_destination(tmp_path, "codex")
    manifest_path = destination / lifecycle.MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["client"] = "claude-code"
    manifest_path.write_text(f"{json.dumps(payload)}\n", encoding="utf-8")

    status = lifecycle.status(tmp_path, "codex")

    assert status.state is SkillState.LOCALLY_MODIFIED
    assert "client mismatch" in status.detail


def test_failed_tree_replacement_restores_original_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interrupted update rolls back the complete prior directory."""

    lifecycle.install(tmp_path, ("codex",))
    destination = lifecycle.client_destination(tmp_path, "codex")
    original = (destination / "SKILL.md").read_text(encoding="utf-8")
    changed = _changed_bundle(resources.load_bundle())
    monkeypatch.setattr(lifecycle.resources, "load_bundle", lambda: changed)
    real_replace = os.replace
    destination_replacements = 0

    def fail_staged_replace(source: str | Path, target: str | Path) -> None:
        nonlocal destination_replacements
        if Path(target) == destination:
            destination_replacements += 1
            if destination_replacements == 1:
                raise OSError("synthetic replace failure")
        real_replace(source, target)

    monkeypatch.setattr(lifecycle.os, "replace", fail_staged_replace)

    with pytest.raises(lifecycle.SkillMutationError, match="rolled back"):
        lifecycle.install(tmp_path, ("codex",))

    assert (destination / "SKILL.md").read_text(encoding="utf-8") == original
    assert lifecycle.status(tmp_path, "codex").state is SkillState.STALE


def test_manifest_is_deterministic_and_complete(tmp_path: Path) -> None:
    """Ownership metadata is stable, sorted, and human-inspectable."""

    lifecycle.install(tmp_path, ("codex",))
    destination = lifecycle.client_destination(tmp_path, "codex")
    manifest_path = destination / lifecycle.MANIFEST_NAME
    text = manifest_path.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert text == f"{json.dumps(payload, indent=2, sort_keys=True)}\n"
    assert payload["schema_version"] == lifecycle.SCHEMA_VERSION
    assert payload["skill"] == resources.SKILL_NAME
    assert payload["client"] == "codex"
    assert set(payload["files"]) == {"SKILL.md", "agents/openai.yaml"}


def test_unsupported_client_fails_before_writes(tmp_path: Path) -> None:
    """Unknown personal client paths are never synthesized."""

    with pytest.raises(ValueError, match="Unsupported skill client"):
        lifecycle.install(tmp_path, ("other",))

    assert list(tmp_path.iterdir()) == []


def _changed_bundle(bundle: SkillBundle) -> SkillBundle:
    files: list[SkillFile] = []
    for item in bundle.files:
        content = (
            f"{item.content}\n# changed\n" if item.relative_path == "SKILL.md" else item.content
        )
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        files.append(SkillFile(item.relative_path, content, digest))
    return SkillBundle(bundle.name, "9.9.9", tuple(files))
