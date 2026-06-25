"""Fail unsafe pip-audit configuration before auditing ambient environments."""

from __future__ import annotations

import sys

MESSAGE = (
    "pip-audit is enabled without pip_audit_args. "
    "Set a pinned input such as pip_audit_args = ['-r', 'config/dev-lock.txt']."
)


def main() -> int:
    """Print the unsafe configuration message and fail."""

    print(MESSAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
