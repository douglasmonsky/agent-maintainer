"""Shared models for guardrail checks and results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    profiles: frozenset[str]
    required_paths: tuple[str, ...] = ()
    required_executable: str | None = None
    optional_skip_reason: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    output: str = ""
    skipped: bool = False
