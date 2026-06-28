"""Compatibility imports repo-local Agent Maintainer hook audit."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

_AUDIT = importlib.import_module("agent_maintainer.hooks.audit")
HookAuditRecord = _AUDIT.HookAuditRecord
record_hook_result = _AUDIT.record_hook_result
status_for_exit = _AUDIT.status_for_exit
