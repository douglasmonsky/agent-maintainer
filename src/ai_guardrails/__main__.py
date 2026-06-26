"""Module entrypoint for `python -m ai_guardrails`."""

from __future__ import annotations

import sys

from ai_guardrails.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
