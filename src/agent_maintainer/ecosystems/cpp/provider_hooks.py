"""Registry-facing hooks owned by the C/C++ ecosystem provider."""

from __future__ import annotations

from collections.abc import Callable

from agent_maintainer.ecosystems.cpp import classification, suppressions
from agent_maintainer.ecosystems.models import SuppressionFinding

SuppressionProvider = Callable[[str, str], tuple[SuppressionFinding, ...]]
classify_path = classification.classify_path
classify_suppression_line = suppressions.classify_line
