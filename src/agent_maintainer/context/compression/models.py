"""Compatibility shim for context compression models."""

from __future__ import annotations

from agent_context.compression import models as _models

CompressionRequest = _models.CompressionRequest
CompressionResult = _models.CompressionResult
validate_non_empty_text = _models.validate_non_empty_text
validate_non_negative = _models.validate_non_negative
validate_terms = _models.validate_terms
