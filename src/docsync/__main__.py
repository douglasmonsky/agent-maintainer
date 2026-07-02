"""Module entrypoint for DocSync."""

from __future__ import annotations

import sys

from docsync.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
