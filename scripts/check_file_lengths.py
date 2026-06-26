#!/usr/bin/env python3
"""Compatibility wrapper for the file-length guardrail check."""

from __future__ import annotations

import sys

from guardrail_lib.checks import file_lengths as _impl

if __name__ == "__main__":
    sys.exit(_impl.main(sys.argv[1:]))

sys.modules[__name__] = _impl
