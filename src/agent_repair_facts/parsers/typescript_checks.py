"""Stable check-name families for TypeScript provider output."""

from __future__ import annotations

TYPESCRIPT_CHECK_FAMILIES = frozenset(
    (
        "typescript-lint",
        "typescript-typecheck",
        "typescript-test",
        "typescript-knip",
        "typescript-dependency-cruiser",
        "typescript-package-manager-audit",
    )
)


def check_family(check: str) -> str:
    """Return the root family for known TypeScript workspace checks."""

    family = check.partition(":")[0]
    return family if family in TYPESCRIPT_CHECK_FAMILIES else check
