"""Module entrypoint for `python -m agent_maintainer`."""

from __future__ import annotations

import sys

from agent_maintainer.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
