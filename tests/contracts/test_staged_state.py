"""Index-authoritative semantic contract orchestration tests."""

from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from agent_maintainer.contracts import service
from agent_maintainer.contracts.baseline import fingerprint, render_baseline
from agent_maintainer.contracts.extractors.cli_manifest import extract_cli_manifest
from agent_maintainer.contracts.models import ContractBaseline, ContractSpec


def test_staged_report_ignores_compatible_unstaged_worktree(tmp_path: Path) -> None:
    """A compatible worktree cannot mask a breaking positional change in the index."""
    repo = tmp_path / "repo"
    repo.mkdir()
    base_files = _write_contract_state(repo, order=("source", "destination"), revision=1, beta=9)
    _git(repo, "init")
    _git(repo, "config", "user.email", "agent-maintainer@example.invalid")
    _git(repo, "config", "user.name", "Agent Maintainer Tests")
    _git(repo, "add", "--", ".agent-maintainer", "config", "pyproject.toml", "CHANGELOG.md")
    _git(repo, "commit", "-m", "base")

    _write_contract_state(repo, order=("destination", "source"), revision=2, beta=10)
    _git(repo, "add", "--", ".agent-maintainer", "config", "pyproject.toml", "CHANGELOG.md")
    _restore_files(repo, base_files)

    report = service.build_contract_report(
        repo,
        base_ref="HEAD",
        mode="check",
        staged=True,
    )

    assert report.errors == ()
    assert report.current_package_version == "0.1.0b10"
    assert any(
        change.classification == "breaking" and change.path.endswith("/arguments/order")
        for change in report.changes
    )
    assert all(obligation.status == "satisfied" for obligation in report.obligations)


def _write_contract_state(
    repo: Path,
    *,
    order: tuple[str, str],
    revision: int,
    beta: int,
) -> dict[str, str]:
    policy = f"""version = 1
package_version_file = "pyproject.toml"
pre_one_breaking = "prerelease"
stable_breaking = "major"

[[contracts]]
id = "copy-cli"
kind = "cli-manifest"
owner = "example.cli"
stability = "beta"
revision = {revision}
source = "config/cli.json"
migration_paths = ["CHANGELOG.md"]
"""
    manifest = {
        "commands": [
            {
                "arguments": [_argument(name) for name in order],
                "exit_statuses": [0],
                "options": [],
                "path": ["copy"],
            }
        ],
        "console_scripts": ["example"],
        "schema_version": 1,
    }
    version = f'[project]\nversion = "0.1.0b{beta}"\n'
    changelog = f"release 0.1.0b{beta}\n"
    files = {
        ".agent-maintainer/contracts.toml": policy,
        "config/cli.json": json.dumps(manifest),
        "pyproject.toml": version,
        "CHANGELOG.md": changelog,
    }
    _restore_files(repo, files)
    spec = ContractSpec(
        id="copy-cli",
        kind="cli-manifest",
        owner="example.cli",
        stability="beta",
        revision=revision,
        source="config/cli.json",
        migration_paths=("CHANGELOG.md",),
    )
    descriptor = extract_cli_manifest(repo, spec)
    semantic = {
        "body": descriptor.body,
        "contract_id": descriptor.contract_id,
        "kind": descriptor.kind,
        "owner": descriptor.owner,
        "revision": descriptor.revision,
        "sources": list(descriptor.sources),
        "stability": descriptor.stability,
    }
    descriptor = replace(descriptor, fingerprint=fingerprint(semantic))
    baseline = render_baseline(
        ContractBaseline(package_version=f"0.1.0b{beta}", descriptors=(descriptor,)),
    )
    baseline_path = repo / ".agent-maintainer/contracts-baseline.json"
    baseline_path.write_text(baseline, encoding="utf-8")
    files[".agent-maintainer/contracts-baseline.json"] = baseline
    return files


def _argument(name: str) -> dict[str, object]:
    return {
        "choices": [],
        "default": None,
        "kind": "path",
        "multiple": False,
        "name": name,
        "required": True,
        "stability": "beta",
    }


def _restore_files(repo: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _git(repo: Path, *arguments: str) -> None:
    subprocess.run(
        ("git", *arguments),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
