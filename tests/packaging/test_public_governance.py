"""Public repository governance contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_URL = "https://github.com/douglasmonsky/agent-maintainer"
PRIVATE_REPORT_URL = f"{REPOSITORY_URL}/security/advisories/new"
POLICY_FILES = (
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
)
ISSUE_TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
ISSUE_FORMS = (
    ISSUE_TEMPLATE_DIR / "bug_report.yml",
    ISSUE_TEMPLATE_DIR / "feature_request.yml",
    ISSUE_TEMPLATE_DIR / "support_request.yml",
)


def test_public_policy_documents_exist_and_are_linked() -> None:
    """First-touch documentation links every public participation policy."""

    readme = _read(REPO_ROOT / "README.md")
    contributing = _read(REPO_ROOT / "CONTRIBUTING.md")

    for filename in POLICY_FILES:
        assert (REPO_ROOT / filename).is_file()
        assert filename in readme
    assert "SECURITY.md" in contributing
    assert "SUPPORT.md" in contributing
    assert "CODE_OF_CONDUCT.md" in contributing


def test_security_and_support_routes_are_private_and_privacy_bounded() -> None:
    """Sensitive reports are routed privately and public logs stay bounded."""

    security = _read(REPO_ROOT / "SECURITY.md")
    support = _read(REPO_ROOT / "SUPPORT.md")

    assert PRIVATE_REPORT_URL in security
    assert "Do not open a public issue with exploit details" in security
    assert "Python 3.11 through 3.14" in support
    assert "no guaranteed response time" in support
    assert "Do not upload an entire" in support
    assert ".verify-logs" in support


def test_contributor_contract_uses_canonical_setup_and_verification() -> None:
    """Contribution guidance stays aligned with repository commands."""

    contributing = _read(REPO_ROOT / "CONTRIBUTING.md")

    for command in ("just bootstrap", "npm ci", "just doctor", "just vp", "just v"):
        assert command in contributing
    assert ".venv/bin/python -m agent_maintainer install --dry-run" in contributing
    assert "CHANGELOG.md" in contributing
    assert "synthetic fixtures" in contributing
    assert "Conventional Commit" in contributing


def test_codeowners_routes_default_and_high_risk_paths() -> None:
    """Default and high-risk repository paths have an explicit owner."""

    lines = {
        line.strip()
        for line in _read(REPO_ROOT / ".github" / "CODEOWNERS").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    required_patterns = {
        "*",
        "/.github/",
        "/SECURITY.md",
        "/config/",
        "/docs/releases/",
        "/osv-scanner.toml",
        "/package-lock.json",
        "/package.json",
        "/pyproject.toml",
        "/src/",
    }

    for pattern in required_patterns:
        assert f"{pattern} @douglasmonsky" in lines


def test_issue_chooser_disables_blank_and_routes_security_privately() -> None:
    """The issue chooser prevents accidental public vulnerability reports."""

    config = _load_yaml(ISSUE_TEMPLATE_DIR / "config.yml")
    links = config["contact_links"]

    assert config["blank_issues_enabled"] is False
    assert any(link["url"] == PRIVATE_REPORT_URL for link in links)
    assert any(link["url"].endswith("/SUPPORT.md") for link in links)


def test_issue_forms_have_unique_required_contract_fields() -> None:
    """Bug, feature, and support intake remains structured and privacy aware."""

    expected_ids = {
        "bug_report.yml": {"release_state", "version", "environment", "reproduction"},
        "feature_request.yml": {"problem", "outcome", "evidence", "constraints"},
        "support_request.yml": {"version", "goal", "attempted", "environment"},
    }

    for path in ISSUE_FORMS:
        form = _load_yaml(path)
        fields = [item for item in form["body"] if "id" in item]
        ids = [field["id"] for field in fields]
        required = {
            field["id"] for field in fields if field.get("validations", {}).get("required") is True
        }

        assert form["name"].strip()
        assert form["description"].strip()
        assert form["title"].strip()
        assert len(ids) == len(set(ids))
        assert required >= expected_ids[path.name]
        assert any("private" in str(field).casefold() for field in fields)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(_read(path))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)
