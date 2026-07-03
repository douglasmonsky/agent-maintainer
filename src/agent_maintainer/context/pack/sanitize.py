"""Compatibility shim for context text sanitizing helpers."""

from __future__ import annotations

from agent_context import sanitize as _sanitize

sanitize_text = _sanitize.sanitize_text
