"""Tests documentation examples keep required proof-repo shape."""

from __future__ import annotations

import tomllib
from pathlib import Path

EXAMPLE_ROOT = Path("examples")
PROOF_EXAMPLES = (
    "context-safe-ratchet",
    "cohesive-change-plan",
    "test-intelligence",
)
REQUIRED_FILES = (
    "README.md",
    "expected-output.md",
    "repair-path.md",
    "pyproject.toml",
)


def test_proof_examples_include_required_docs_and_config() -> None:
    """Proof examples include docs, config, source, and tests."""

    for example in PROOF_EXAMPLES:
        example_root = EXAMPLE_ROOT / example
        for relative_path in REQUIRED_FILES:
            assert (example_root / relative_path).exists(), example
        assert tuple((example_root / "src").rglob("*.py")), example
        assert tuple((example_root / "tests").rglob("test_*.py")), example


def test_proof_example_pyprojects_parse() -> None:
    """Proof example TOML files parse and define Agent Maintainer config."""

    for example in PROOF_EXAMPLES:
        pyproject = EXAMPLE_ROOT / example / "pyproject.toml"
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        assert "agent_maintainer" in payload["tool"], example
