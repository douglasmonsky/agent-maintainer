"""Strict path-risk TOML policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.verification_plan import policy as policy_loader


# docsync:evidence.start evidence.readme.path_risk_policy_tests
def test_missing_policy_is_unconfigured(tmp_path: Path) -> None:
    assert policy_loader.load_policy(tmp_path / "missing.toml") is None


def test_load_policy_decodes_complete_contract(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path,
        """
version = 1

[[rules]]
id = "architecture-policy"
description = "Architecture changes require proof."
paths = ["tach.toml", "src/**/tach.domain.toml"]
mode = "required"
profiles = ["precommit"]
checks = ["tach-config", "tach"]
review_categories = ["architecture"]

[[rules.evidence]]
id = "architecture-decision"
kind = "changed-path"
paths = ["docs/architecture/decisions/*.md"]
minimum = 1
message = "Add or update an architecture decision record."
""",
    )

    policy = policy_loader.load_policy(policy_path)

    assert policy is not None
    assert policy.path == policy_path.as_posix()
    assert policy.version == 1
    rule = policy.rules[0]
    assert rule.id == "architecture-policy"
    assert rule.mode == "required"
    assert rule.profiles == ("precommit",)
    assert rule.checks == ("tach-config", "tach")
    assert rule.review_categories == ("architecture",)
    assert rule.evidence[0].id == "architecture-decision"
    assert rule.evidence[0].minimum == 1


def test_load_policy_defaults_rule_to_advisory(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path,
        'version = 1\n[[rules]]\nid = "docs"\npaths = ["docs/**"]\n',
    )

    policy = policy_loader.load_policy(policy_path)

    assert policy is not None
    assert policy.rules[0].mode == "advisory"
    assert policy.rules[0].evidence == ()


@pytest.mark.parametrize(
    ("document", "message"),
    (
        ("rules = []\n", "version"),
        ("version = 2\n", "version"),
        ("version = true\n", "version"),
        ("version = 1\nunknown = true\n", "unknown top-level"),
        ("version = 1\nrules = {}\n", "rules"),
        ('version = 1\n[[rules]]\npaths = ["src/**"]\n', "id"),
        ('version = 1\n[[rules]]\nid = "Bad ID"\npaths = ["src/**"]\n', "id"),
        ('version = 1\n[[rules]]\nid = "source"\npaths = []\n', "paths"),
        ('version = 1\n[[rules]]\nid = "source"\npaths = ["../src"]\n', "paths"),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\nmode = "block"\n',
            "mode",
        ),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\nextra = true\n',
            "unknown rule",
        ),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\n'
            'review_categories = ["Bad Category"]\n',
            "review_categories",
        ),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**", "src/**"]\n',
            "duplicate",
        ),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\n'
            '[[rules.evidence]]\nid = "tests"\nkind = "artifact"\n'
            'paths = ["tests/**"]\n',
            "kind",
        ),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\n'
            '[[rules.evidence]]\nid = "tests"\nkind = "changed-path"\n'
            'paths = ["tests/**"]\nminimum = 0\n',
            "minimum",
        ),
        (
            'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\n'
            '[[rules.evidence]]\nid = "tests"\nkind = "changed-path"\n'
            'paths = ["tests/**"]\nextra = true\n',
            "unknown evidence",
        ),
    ),
)
def test_invalid_policy_fails_closed(
    tmp_path: Path,
    document: str,
    message: str,
) -> None:
    policy_path = _write_policy(tmp_path, document)

    with pytest.raises(policy_loader.PolicyError, match=message):
        policy_loader.load_policy(policy_path)


def test_duplicate_rule_and_evidence_ids_fail_closed(tmp_path: Path) -> None:
    duplicate_rules = _write_policy(
        tmp_path,
        'version = 1\n[[rules]]\nid = "same"\npaths = ["a"]\n'
        '[[rules]]\nid = "same"\npaths = ["b"]\n',
    )
    with pytest.raises(policy_loader.PolicyError, match="duplicate rule id"):
        policy_loader.load_policy(duplicate_rules)

    duplicate_evidence = _write_policy(
        tmp_path,
        'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\n'
        '[[rules.evidence]]\nid = "same"\nkind = "changed-path"\n'
        'paths = ["tests/**"]\n[[rules.evidence]]\nid = "same"\n'
        'kind = "changed-path"\npaths = ["docs/**"]\n',
    )
    with pytest.raises(policy_loader.PolicyError, match="duplicate evidence id"):
        policy_loader.load_policy(duplicate_evidence)


def test_catalog_names_are_validated_against_exact_configured_contract(
    tmp_path: Path,
) -> None:
    policy_path = _write_policy(
        tmp_path,
        'version = 1\n[[rules]]\nid = "source"\npaths = ["src/**"]\n'
        'profiles = ["precommit"]\nchecks = ["tach"]\n',
    )
    policy = policy_loader.load_policy(policy_path)
    assert policy is not None

    policy_loader.validate_catalog_names(
        policy,
        profiles=("fast", "precommit"),
        checks=("ruff", "tach"),
    )
    with pytest.raises(policy_loader.PolicyError, match="unknown profile"):
        policy_loader.validate_catalog_names(
            policy,
            profiles=("fast",),
            checks=("tach",),
        )
    with pytest.raises(policy_loader.PolicyError, match="unknown check"):
        policy_loader.validate_catalog_names(
            policy,
            profiles=("precommit",),
            checks=("ruff",),
        )
    with pytest.raises(policy_loader.PolicyError, match="duplicate configured check"):
        policy_loader.validate_catalog_names(
            policy,
            profiles=("precommit",),
            checks=("tach", "tach"),
        )


def test_repository_policy_covers_lock_security_and_release_surfaces() -> None:
    policy = policy_loader.load_policy(Path(".agent-maintainer/path-risk.toml"))
    assert policy is not None
    patterns = {rule.id: set(rule.paths) for rule in policy.rules}

    assert "config/dev-lock.txt" in patterns["dependency-contract"]
    assert "package-lock.json" in patterns["dependency-contract"]
    assert "semgrep.yml" in patterns["security-policy"]
    assert "osv-scanner.toml" in patterns["security-policy"]
    assert "pyproject.toml" in patterns["release-contract"]


def _write_policy(tmp_path: Path, document: str) -> Path:
    path = tmp_path / "path-risk.toml"
    path.write_text(document.strip() + "\n", encoding="utf-8")
    return path


# docsync:evidence.end evidence.readme.path_risk_policy_tests
