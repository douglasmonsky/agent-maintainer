"""Shared doctor diagnostic result types."""

from __future__ import annotations

from dataclasses import dataclass

Status = str
State = str

OK: Status = "PASS"
WARNING: Status = "WARN"
ERROR: Status = "FAIL"

ACTIVE: State = "active"
DISABLED: State = "disabled"
MISSING: State = "missing"
NOT_APPLICABLE: State = "not applicable"
UNSAFE_CONFIG: State = "unsafe config"


@dataclass(frozen=True)
class DoctorResult:
    """One setup diagnostic row emitted by the doctor command."""

    name: str
    status: Status
    message: str
    state: State = ACTIVE
    hint: str = ""
