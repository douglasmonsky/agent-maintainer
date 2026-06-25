"""Shared doctor diagnostic result types."""

from __future__ import annotations

from dataclasses import dataclass

Status = str

OK: Status = "PASS"
WARNING: Status = "WARN"
ERROR: Status = "FAIL"


@dataclass(frozen=True)
class DoctorResult:
    """One setup diagnostic row emitted by the doctor command."""

    name: str
    status: Status
    message: str
