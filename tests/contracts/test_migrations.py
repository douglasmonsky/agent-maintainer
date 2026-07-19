"""Breaking-contract migration-evidence obligation tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agent_maintainer.contracts.migrations import migration_obligations
from agent_maintainer.contracts.models import (
    ContractChange,
    ContractPolicy,
    ContractSpec,
)
from agent_maintainer.ecosystems.git_changes import GitPathChange


def _policy(
    *paths: str,
    contract_id: str = "public-api",
) -> ContractPolicy:
    return ContractPolicy(
        contracts=(
            ContractSpec(
                id=contract_id,
                kind="json-schema",
                owner="public.api",
                stability="beta",
                revision=2,
                source="schemas/public.json",
                migration_paths=paths,
            ),
        )
    )


def _breaking(
    fingerprint: str = "sha256:" + "a" * 64,
    *,
    contract_id: str = "public-api",
) -> ContractChange:
    return ContractChange(
        contract_id=contract_id,
        operation="member-remove",
        path="/properties/value",
        before={"required": False},
        after=None,
        classification="breaking",
        fingerprint=fingerprint,
        reason="test break",
    )


@pytest.mark.parametrize("kind", ("added", "modified"))
def test_current_migration_document_satisfies_break(kind: str) -> None:
    """Added and modified current paths are valid migration evidence."""
    obligations = migration_obligations(
        _policy("docs/upgrading.md"),
        (_breaking(),),
        (GitPathChange("docs/upgrading.md", kind),),
    )

    assert obligations[0].status == "satisfied"
    assert obligations[0].fingerprints == ("sha256:" + "a" * 64,)
    assert obligations[0].missing_paths == ()


def test_renamed_destination_satisfies_but_deleted_source_does_not() -> None:
    """Only a rename destination present after the change can prove evidence."""
    renamed = migration_obligations(
        _policy("docs/new.md"),
        (_breaking(),),
        (GitPathChange("docs/new.md", "renamed", old_path="docs/old.md"),),
    )
    deleted = migration_obligations(
        _policy("docs/old.md"),
        (_breaking(),),
        (GitPathChange("docs/old.md", "deleted"),),
    )

    assert renamed[0].status == "satisfied"
    assert deleted[0].status == "unresolved"
    assert deleted[0].missing_paths == ("docs/old.md",)


@pytest.mark.parametrize("kind", ("copied", "type-changed", "unmerged"))
def test_non_evidence_change_kinds_do_not_satisfy_break(kind: str) -> None:
    """Only authored add/edit/rename destination facts count as migration work."""
    obligations = migration_obligations(
        _policy("docs/upgrading.md"),
        (_breaking(),),
        (GitPathChange("docs/upgrading.md", kind),),
    )

    assert obligations[0].status == "unresolved"


def test_evidence_for_another_contract_cannot_satisfy_break() -> None:
    """Migration paths remain scoped to the exact breaking contract."""
    policy = ContractPolicy(
        contracts=(
            _policy("docs/first.md", contract_id="first").contracts[0],
            _policy("docs/second.md", contract_id="second").contracts[0],
        )
    )

    obligations = migration_obligations(
        policy,
        (_breaking(contract_id="first"),),
        (GitPathChange("docs/second.md", "modified"),),
    )

    assert obligations[0].contract_id == "first"
    assert obligations[0].status == "unresolved"
    assert obligations[0].missing_paths == ("docs/first.md",)


@pytest.mark.parametrize(
    "path",
    ("docs/migrations-extra/guide.md", "docs/migrations/nested/guide.md"),
)
def test_segment_aware_pattern_rejects_prefix_and_depth_confusion(path: str) -> None:
    """A single-star segment cannot cross directory boundaries or prefixes."""
    obligations = migration_obligations(
        _policy("docs/migrations/*.md"),
        (_breaking(),),
        (GitPathChange(path, "modified"),),
    )

    assert obligations[0].status == "unresolved"


def test_segment_aware_pattern_accepts_exact_wildcard_segment() -> None:
    """A configured filename wildcard matches within its exact path segment."""
    obligations = migration_obligations(
        _policy("docs/upgrading-to-*.md"),
        (_breaking(),),
        (GitPathChange("docs/upgrading-to-v2.md", "modified"),),
    )

    assert obligations[0].status == "satisfied"


def test_missing_migration_configuration_reports_breaking_fingerprints() -> None:
    """A break with no configured evidence path stays explicit and actionable."""
    fingerprints = ("sha256:" + "a" * 64, "sha256:" + "b" * 64)
    obligations = migration_obligations(
        _policy(),
        tuple(_breaking(item) for item in fingerprints),
        (),
    )

    assert obligations[0].status == "unresolved"
    assert obligations[0].fingerprints == fingerprints
    assert obligations[0].missing_paths == ()


def test_nonbreaking_change_creates_no_migration_obligation() -> None:
    """Compatible additions never demand migration evidence."""
    compatible = replace(_breaking(), classification="compatible", operation="member-add")

    assert migration_obligations(_policy("docs/upgrading.md"), (compatible,), ()) == ()
