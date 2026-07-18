"""Segment-aware path-risk matching tests."""

from __future__ import annotations

import pytest

from agent_maintainer.verification_plan.matching import (
    PathPatternError,
    path_matches,
    validate_repo_pattern,
)


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    (
        ("tach.toml", "tach.toml", True),
        ("src/*/tach.domain.toml", "src/api/tach.domain.toml", True),
        ("src/*/tach.domain.toml", "src/api/deep/tach.domain.toml", False),
        ("src/**/tach.domain.toml", "src/tach.domain.toml", True),
        ("src/**/tach.domain.toml", "src/api/deep/tach.domain.toml", True),
        ("**/package.json", "package.json", True),
        ("**/package.json", "packages/web/package.json", True),
        ("src/?.py", "src/a.py", True),
        ("src/?.py", "src/ab.py", False),
        ("README.md", "readme.md", False),
    ),
)
def test_path_matches_segment_contract(
    pattern: str,
    path: str,
    expected: bool,
) -> None:
    assert path_matches(pattern, path) is expected


@pytest.mark.parametrize(
    "pattern",
    (
        "",
        "/root",
        "./src/**",
        "src\\**",
        "src//x",
        "src/./x",
        "src/../x",
        "src/**x",
        "src/x**",
        "src/\0x",
    ),
)
def test_invalid_policy_patterns_fail_closed(pattern: str) -> None:
    with pytest.raises(PathPatternError, match=r"rules\[0\]\.paths\[0\]"):
        validate_repo_pattern(pattern, label="rules[0].paths[0]")


def test_path_matches_rejects_invalid_changed_path() -> None:
    with pytest.raises(PathPatternError, match="path"):
        path_matches("src/**", "src/../secret.txt")


def test_path_matching_handles_adversarial_depth_without_recursion() -> None:
    pattern = "/".join((*(("**",) * 1100), "target.txt"))

    assert path_matches(pattern, "target.txt")
