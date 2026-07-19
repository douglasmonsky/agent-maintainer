"""Strict authored contract policy tests."""

from pathlib import Path

import pytest

from agent_maintainer.contracts.models import PolicyError
from agent_maintainer.contracts.policy import load_policy, parse_policy

VALID_POLICY = """version = 1
package_version_file = "pyproject.toml"
pre_one_breaking = "prerelease"
stable_breaking = "major"

[[contracts]]
id = "docsync-api"
kind = "python-api"
owner = "docsync.api"
stability = "beta"
revision = 1
source = "src/docsync/api.py"
exports = ["*"]
migration_paths = ["CHANGELOG.md"]

[[decisions]]
contract = "docsync-api"
fingerprint = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
classification = "breaking"
reason = "Documented beta migration."
"""


def test_policy_loads_exact_contract_and_decision(tmp_path: Path) -> None:
    """Valid policy produces sorted immutable declarations."""
    policy_path = tmp_path / ".agent-maintainer/contracts.toml"
    policy_path.parent.mkdir()
    policy_path.write_text(VALID_POLICY, encoding="utf-8")

    policy = load_policy(tmp_path)

    assert policy is not None
    assert policy.contracts[0].id == "docsync-api"
    assert policy.contracts[0].exports == ("*",)
    assert policy.decisions[0].classification == "breaking"


@pytest.mark.parametrize(
    ("replacement", "message"),
    (
        ("version = 0", "version"),
        ("version = 2", "version"),
        ('source = "../api.py"', "unsafe or ambiguous"),
        ('fingerprint = "sha256:*"', "fingerprint"),
        ('kind = "runtime-reflection"', "kind"),
        ("unknown = true", "unknown"),
    ),
)
def test_policy_rejects_invalid_exact_values(replacement: str, message: str) -> None:
    """Unsafe or unsupported authored values fail closed."""
    if replacement.startswith("version"):
        text = VALID_POLICY.replace("version = 1", replacement, 1)
    elif replacement.startswith("unknown"):
        text = f"{VALID_POLICY}\n{replacement}\n"
    else:
        key = replacement.partition(" = ")[0]
        original = next(line for line in VALID_POLICY.splitlines() if line.startswith(f"{key} = "))
        text = VALID_POLICY.replace(original, replacement, 1)

    with pytest.raises(PolicyError, match=message):
        parse_policy(text, source="contracts.toml")


def test_policy_requires_version() -> None:
    """The policy schema version cannot be inferred from absent input."""
    text = VALID_POLICY.replace("version = 1\n", "", 1)

    with pytest.raises(PolicyError, match="version"):
        parse_policy(text, source="contracts.toml")


@pytest.mark.parametrize(
    ("text", "message"),
    (
        (
            VALID_POLICY.replace("\n[[contracts]]", "\nunknown = true\n\n[[contracts]]", 1),
            "unknown top-level",
        ),
        (
            VALID_POLICY.replace("\n[[decisions]]", "\nunknown = true\n\n[[decisions]]", 1),
            "unknown contract",
        ),
        (f"{VALID_POLICY}\nunknown = true\n", "unknown decision"),
    ),
)
def test_policy_rejects_unknown_keys_at_every_level(text: str, message: str) -> None:
    """Unknown authored policy cannot be silently ignored at any nesting level."""
    with pytest.raises(PolicyError, match=message):
        parse_policy(text, source="contracts.toml")


@pytest.mark.parametrize(
    ("original", "replacement", "message"),
    (
        ('owner = "docsync.api"', 'owner = "docsync-api"', "owner"),
        ('stability = "beta"', 'stability = "experimental"', "stability"),
        ("revision = 1", "revision = 0", "revision"),
        ('source = "src/docsync/api.py"', 'source = "/src/docsync/api.py"', "repository-relative"),
        ('source = "src/docsync/api.py"', 'source = "src\\\\docsync\\\\api.py"', "POSIX"),
        ('migration_paths = ["CHANGELOG.md"]', 'migration_paths = [""]', "non-empty"),
        ('kind = "python-api"', 'kind = "config-capabilities"', "exports"),
    ),
)
def test_policy_rejects_invalid_contract_fields(
    original: str,
    replacement: str,
    message: str,
) -> None:
    """Contract fields are exact, bounded, and kind-specific."""
    text = VALID_POLICY.replace(original, replacement, 1)

    with pytest.raises(PolicyError, match=message):
        parse_policy(text, source="contracts.toml")


def test_policy_rejects_duplicate_decision_fingerprint() -> None:
    """Two authored decisions cannot claim the same exact contract change."""
    duplicate = (
        VALID_POLICY
        + """
[[decisions]]
contract = "docsync-api"
fingerprint = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
classification = "breaking"
reason = "Duplicate decision."
"""
    )

    with pytest.raises(PolicyError, match="duplicate decision fingerprint"):
        parse_policy(duplicate, source="contracts.toml")


def test_policy_rejects_non_text_array_members() -> None:
    """Malformed arrays raise a policy error instead of leaking a type error."""
    text = VALID_POLICY.replace('exports = ["*"]', 'exports = [["*"]]')

    with pytest.raises(PolicyError, match="array of text"):
        parse_policy(text, source="contracts.toml")


def test_policy_rejects_duplicate_contract_ids() -> None:
    """Contract identity cannot be shadowed later in the policy."""
    duplicate = (
        VALID_POLICY
        + """
[[contracts]]
id = "docsync-api"
kind = "python-api"
owner = "docsync.api"
stability = "beta"
revision = 1
source = "src/docsync/api.py"
"""
    )

    with pytest.raises(PolicyError, match="duplicate contract"):
        parse_policy(duplicate, source="contracts.toml")


def test_missing_policy_is_advisory_absence(tmp_path: Path) -> None:
    """Repositories without authored policy receive no configured ratchet."""
    assert load_policy(tmp_path) is None
