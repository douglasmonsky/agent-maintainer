"""Module entrypoint for Archguard."""

from __future__ import annotations

import sys

from archguard.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
