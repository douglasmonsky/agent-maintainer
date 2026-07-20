"""Shared raw record contract for package-manager audit adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawAuditRecord:
    """One adapter-owned record before shared normalization."""

    package: object
    severity: object
    advisory_ids: tuple[object, ...] = ()
    vulnerable_ranges: tuple[object, ...] = ()
    fixed_versions: tuple[object, ...] = ()
    scope: object = ""
    directness: object = ""
    path: object = ""
    title: object = ""
