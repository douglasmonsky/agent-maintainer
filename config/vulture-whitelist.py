"""Vulture whitelist for dynamic entry points and framework callbacks."""

from docsync.cli import console_main

VULTURE_WHITELIST = (console_main,)

__all__ = ["VULTURE_WHITELIST"]
