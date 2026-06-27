"""Compatibility wrapper for Archguard Tach config validation."""

from __future__ import annotations

import sys

from archguard.cli import tach_config_main as main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
