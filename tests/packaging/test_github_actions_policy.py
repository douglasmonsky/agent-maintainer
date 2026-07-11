"""Tests for GitHub Actions hardening policy files."""

from __future__ import annotations

import re
import tomllib

from tests.support.paths import REPO_ROOT

DEEP_VERIFY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deep-verify.yml"
VERIFY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "verify.yml"
PUBLISH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish.yml"
WORKFLOWS = (VERIFY_WORKFLOW, DEEP_VERIFY_WORKFLOW, PUBLISH_WORKFLOW)
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
ACTION_PINS = {
    "actions/checkout": ("9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0", "v7"),
    "actions/download-artifact": ("3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c", "v8"),
    "actions/setup-python": ("ece7cb06caefa5fff74198d8649806c4678c61a1", "v6.3.0"),
    "actions/setup-node": ("48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e", "v6.4.0"),
    "actions/upload-artifact": ("043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "v7"),
    "pypa/gh-action-pypi-publish": (
        "cef221092ed1bacb1cc03d23a2d87d1d172e277b",
        "release/v1",
    ),
}


def test_verify_workflow_declares_read_only_contents_permission() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "\npermissions:\n  contents: read\n" in workflow


def test_checkout_does_not_persist_credentials() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "persist-credentials: false" in workflow


def test_verify_workflow_disables_python_bytecode_writes() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert 'PYTHONDONTWRITEBYTECODE: "1"' in workflow


def test_python_compatibility_matrix_smokes_built_distributions() -> None:
    """Every supported Python installs manual tooling and smokes artifacts."""

    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")
    normalized = " ".join(workflow.split())

    assert 'python-version: ["3.11", "3.12", "3.13", "3.14"]' in workflow
    assert 'AGENT_MAINTAINER_RUN_RELEASE_TESTS: "1"' in workflow
    assert (
        'python -m pip install -c config/dev-lock.txt -e ".[core,manual]" build twine' in normalized
    )
    assert (
        "python -m pytest -m artifact_smoke tests/release/test_release_packaging.py -q"
    ) in normalized


def test_verify_workflow_installs_gitleaks_from_release_artifact() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "GITLEAKS_VERSION=8.30.1" in workflow
    assert "GITLEAKS_SHA256=" in workflow
    assert "sha256sum" in workflow
    assert 'test "$ACTUAL_SHA256" = "$GITLEAKS_SHA256"' in workflow
    assert "github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}" in workflow
    assert "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" in workflow
    assert "go install github.com/gitleaks/gitleaks" not in workflow


def test_verify_workflow_installs_node_backed_external_tools() -> None:
    workflow = VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "npm ci" in workflow
    assert "npm install -g" not in workflow


def test_workflows_with_npm_use_pinned_node_22() -> None:
    """Node-backed gates never inherit a mutable runner toolchain."""

    setup_node = ACTION_PINS["actions/setup-node"]
    expected_use = f"uses: actions/setup-node@{setup_node[0]} # {setup_node[1]}"
    for path in WORKFLOWS:
        workflow = path.read_text(encoding="utf-8")
        if "npm ci" not in workflow:
            continue
        assert expected_use in workflow
        assert 'node-version: "22"' in workflow
        assert "package-manager-cache: false" in workflow


def test_deep_verify_workflow_runs_scheduled_manual_security_profiles() -> None:
    """Slow profiles have an automated cadence outside normal PR CI."""
    workflow = DEEP_VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "python3 -m agent_maintainer verify --profile security" in workflow
    assert "python3 -m agent_maintainer verify --profile manual" in workflow
    assert "\npermissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert 'PYTHONDONTWRITEBYTECODE: "1"' in workflow


def test_deep_verify_workflow_installs_required_external_tools() -> None:
    """Scheduled deep checks install external binaries they dogfood."""
    workflow = DEEP_VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "npm ci" in workflow
    assert "GITLEAKS_VERSION=8.30.1" in workflow
    assert "OSV_SCANNER_VERSION=2.4.0" in workflow
    assert "sha256sum" in workflow
    assert "python -m pip install -e ." in workflow


def test_dependabot_updates_hash_pinned_github_actions() -> None:
    dependabot = (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'directory: "/"' in dependabot
    assert 'interval: "weekly"' in dependabot
    assert "default-days: 7" in dependabot


def test_every_workflow_action_is_hash_pinned_with_update_comment() -> None:
    """Every remote action has immutable code identity and updater metadata."""

    for workflow in WORKFLOWS:
        uses_lines = [
            line.strip()
            for line in workflow.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("uses:")
        ]
        assert uses_lines
        for line in uses_lines:
            target, separator, comment = line.removeprefix("uses:").partition(" # ")
            action, at, reference = target.strip().rpartition("@")
            assert at == "@", line
            assert FULL_SHA.fullmatch(reference), line
            assert separator == " # ", line
            assert (reference, comment.strip()) == ACTION_PINS[action], line


def test_zizmor_config_requires_hash_pinning_for_every_namespace() -> None:
    config = (REPO_ROOT / "zizmor.yml").read_text(encoding="utf-8")

    assert "unpinned-uses:" in config
    assert '"*": hash-pin' in config
    assert "ref-pin" not in config


def test_every_workflow_is_schema_validated() -> None:
    """The configured schema gate cannot omit the scheduled deep workflow."""

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    args = pyproject["tool"]["agent_maintainer"]["check_jsonschema_args"]
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")

    for workflow in WORKFLOWS:
        relative = workflow.relative_to(REPO_ROOT).as_posix()
        assert relative in args
        assert relative in justfile


def test_workflow_concurrency_cancels_only_replaceable_validation() -> None:
    """Release and deep evidence runs finish; superseded PR CI may cancel."""

    verify = VERIFY_WORKFLOW.read_text(encoding="utf-8")
    deep = DEEP_VERIFY_WORKFLOW.read_text(encoding="utf-8")
    publish = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "group: verify-${{ github.workflow }}-${{ github.ref }}" in verify
    assert "cancel-in-progress: true" in verify
    assert "group: deep-verify-${{ github.workflow }}-${{ github.ref }}" in deep
    assert "cancel-in-progress: false" in deep
    assert "group: publish-${{ github.workflow }}-${{ github.ref }}" in publish
    assert "cancel-in-progress: false" in publish
