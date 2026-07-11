"""Vulture whitelist for dynamic entry points and framework callbacks."""

from docsync.cli import console_main
from tests.conftest import pytest_configure

VULTURE_WHITELIST = (console_main, pytest_configure)

__all__ = ["VULTURE_WHITELIST"]
