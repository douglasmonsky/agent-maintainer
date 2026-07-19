"""Contract revision and package-version obligation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from packaging.version import Version

from agent_maintainer.contracts.models import (
    Classification,
    ContractChange,
    ContractPolicy,
    ContractSpec,
    VersionImpact,
)
from agent_maintainer.contracts.versioning import (
    contract_revision_obligations,
    package_version_obligation,
    read_package_version,
    recommended_version,
)


def _spec(
    contract_id: str = "public-api",
    *,
    revision: int = 1,
    stability: str = "stable",
) -> ContractSpec:
    return ContractSpec(
        id=contract_id,
        kind="json-schema",
        owner="public.api",
        stability=stability,
        revision=revision,
        source="schemas/public.json",
    )


def _policy(*specs: ContractSpec) -> ContractPolicy:
    return ContractPolicy(
        pre_one_breaking="prerelease",
        stable_breaking="major",
        contracts=tuple(specs),
    )


def _change(
    *,
    contract_id: str = "public-api",
    operation: str = "member-remove",
    classification: Classification = "breaking",
    fingerprint: str = "sha256:" + "a" * 64,
) -> ContractChange:
    return ContractChange(
        contract_id=contract_id,
        operation=operation,
        path="/properties/value",
        before={"required": False},
        after=None,
        classification=classification,
        fingerprint=fingerprint,
        reason="test change",
    )


@pytest.mark.parametrize(
    ("current_revision", "status"),
    ((1, "unresolved"), (2, "satisfied"), (3, "unresolved")),
)
def test_breaking_contract_requires_exactly_one_revision(
    current_revision: int,
    status: str,
) -> None:
    """Breaking drift accepts exactly base revision plus one."""
    obligations = contract_revision_obligations(
        _policy(_spec(revision=1)),
        _policy(_spec(revision=current_revision)),
        (_change(),),
    )

    assert len(obligations) == 1
    assert obligations[0].kind == "contract-revision"
    assert obligations[0].status == status
    assert obligations[0].current == str(current_revision)
    assert obligations[0].expected == "2"
    assert obligations[0].fingerprints == ("sha256:" + "a" * 64,)


@pytest.mark.parametrize("current_revision", (0, 2))
def test_compatible_or_driftless_contract_rejects_revision_change(
    current_revision: int,
) -> None:
    """Decrease and unearned revision growth are independently unresolved."""
    changes = () if current_revision > 1 else (_change(classification="compatible"),)

    obligations = contract_revision_obligations(
        _policy(_spec(revision=1)),
        _policy(_spec(revision=current_revision)),
        changes,
    )

    assert obligations[0].status == "unresolved"
    assert obligations[0].expected == "1"


def test_compatible_change_may_keep_revision_stable() -> None:
    """Compatible semantic drift does not force a contract revision."""
    obligations = contract_revision_obligations(
        _policy(_spec(revision=1)),
        _policy(_spec(revision=1)),
        (_change(classification="compatible", operation="member-add"),),
    )

    assert obligations[0].status == "satisfied"


def test_new_contract_starts_at_one_and_removed_contract_is_unresolved() -> None:
    """New identity starts at one; removal cannot hide its revision obligation."""
    new = contract_revision_obligations(
        _policy(),
        _policy(_spec(revision=1)),
        (_change(operation="contract-add", classification="compatible"),),
    )
    removed = contract_revision_obligations(
        _policy(_spec(revision=1)),
        _policy(),
        (_change(operation="contract-remove"),),
    )

    assert new[0].status == "satisfied"
    assert new[0].expected == "1"
    assert removed[0].status == "unresolved"
    assert removed[0].current == "missing"


@pytest.mark.parametrize(
    ("base", "impact", "expected"),
    (
        ("0.1.0b9", "prerelease", "0.1.0b10"),
        ("1.4.2", "patch", "1.4.3"),
        ("1.4.2", "minor", "1.5.0"),
        ("1.4.2", "major", "2.0.0"),
        ("1.4.2+local.1", "patch", "1.4.3"),
        ("1.4.2.dev4", "minor", "1.5.0"),
    ),
)
def test_recommended_versions(base: str, impact: VersionImpact, expected: str) -> None:
    """Concrete stable and prerelease recommendations normalize local/dev state."""
    recommendation = recommended_version(Version(base), impact)

    assert recommendation is not None
    assert str(recommendation) == expected


def test_final_to_prerelease_recommendation_is_ambiguous() -> None:
    """A final release has no uniquely correct next prerelease line."""
    assert recommended_version(Version("1.4.2"), "prerelease") is None


PackageCase = tuple[str, str, Classification, str, str, VersionImpact, str]


@pytest.mark.parametrize(
    "case",
    (
        ("stable", "member-remove", "breaking", "1.4.2", "2.0.0", "major", "satisfied"),
        ("stable", "member-add", "compatible", "1.4.2", "1.5.0", "minor", "satisfied"),
        ("stable", "constraint-change", "compatible", "1.4.2", "1.4.3", "patch", "satisfied"),
        ("beta", "member-remove", "breaking", "0.1.0b9", "0.1.0b10", "prerelease", "satisfied"),
        ("stable", "member-remove", "breaking", "1.4.2", "1.9.9", "major", "unresolved"),
        ("stable", "member-remove", "breaking", "1.4.2", "2.1.0", "major", "satisfied"),
    ),
)
def test_package_version_obligation_matrix(
    case: PackageCase,
) -> None:
    """The strongest semantic impact yields one minimum-version obligation."""
    stability, operation, classification, base, current, impact, status = case
    obligation = package_version_obligation(
        base,
        current,
        _policy(_spec(stability=stability)),
        (_change(operation=operation, classification=classification),),
    )

    assert obligation.minimum_impact == impact
    assert obligation.status == status


def test_ambiguous_or_invalid_versions_are_unresolved() -> None:
    """Invalid input and final-to-prerelease ambiguity become bounded obligations."""
    invalid = package_version_obligation(
        "not-a-version",
        "1.0.0",
        _policy(_spec(stability="beta")),
        (_change(),),
    )
    ambiguous = package_version_obligation(
        "1.0.0",
        "1.0.1",
        _policy(_spec(stability="beta")),
        (_change(),),
    )

    assert invalid.status == "unresolved"
    assert ambiguous.status == "unresolved"
    assert ambiguous.expected == "ambiguous"


def test_read_package_version_reads_exact_project_value(tmp_path: Path) -> None:
    """The configured TOML source yields only the exact project version text."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    assert read_package_version(tmp_path, "pyproject.toml") == "1.2.3"


@pytest.mark.parametrize(
    ("text", "message"),
    (
        ('[project]\nname = "demo"\n', "version"),
        ("[project]\nversion = 1\n", "text"),
        ('[project]\ndynamic = ["version"]\n', "version"),
        ('version = "1.2.3"\n', "project"),
    ),
)
def test_read_package_version_rejects_missing_or_malformed_metadata(
    tmp_path: Path,
    text: str,
    message: str,
) -> None:
    """Dynamic, missing, non-text, and misplaced versions fail closed."""
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        read_package_version(tmp_path, "pyproject.toml")


def test_read_package_version_rejects_unsafe_path(tmp_path: Path) -> None:
    """Package metadata reads stay confined to the repository."""
    with pytest.raises(ValueError, match=r"unsafe|ambiguous"):
        read_package_version(tmp_path, "../pyproject.toml")
