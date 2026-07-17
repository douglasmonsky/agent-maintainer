"""Read-only Spotless native-ratchet validation and rendering."""

from __future__ import annotations

import re

# Security: every invocation below is a fixed, read-only Git probe.
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5.0
SAFE_RATCHET_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
FORBIDDEN_REF_PARTS = ("..", "//", "@{")


@dataclass(frozen=True)
class SpotlessRatchetValidation:
    """Availability and bounded CI guidance for one explicit Git reference."""

    ref: str
    available: bool
    shallow: bool
    reason: str
    ci_fetch_guidance: str


def validate_spotless_ratchet_ref(
    root: Path,
    ref: str,
) -> SpotlessRatchetValidation:
    """Check an explicit commit-ish without fetching or mutating the repository."""
    invalid_reason = _invalid_ref_reason(ref)
    if invalid_reason:
        return SpotlessRatchetValidation(ref, False, False, invalid_reason, "")
    try:
        available, shallow = _probe_ref(root, ref)
    except (OSError, subprocess.SubprocessError):
        available = False
        shallow = False
    if available:
        return SpotlessRatchetValidation(ref, True, False, "reference is available", "")
    checkout_kind = "shallow checkout" if shallow else "repository"
    return SpotlessRatchetValidation(
        ref,
        False,
        shallow,
        f"Spotless ratchet reference `{ref}` is unavailable in this {checkout_kind}.",
        (
            f"CI must fetch `{ref}` before verification; configure checkout with "
            "`fetch-depth: 0` or an explicit fetch for that ref."
        ),
    )


def render_spotless_ratchet(build_text: str, dsl: str, ref: str) -> str:
    """Add ratchetFrom to a rendered, Agent-Maintainer-owned build fragment."""
    invalid_reason = _invalid_ref_reason(ref)
    if invalid_reason:
        raise ValueError(invalid_reason)
    marker = "spotless {\n"
    if marker not in build_text:
        raise ValueError("rendered Java build fragment has no Spotless block")
    statement = f'    ratchetFrom("{ref}")\n' if dsl == "kotlin" else f"    ratchetFrom '{ref}'\n"
    return build_text.replace(marker, f"{marker}{statement}", 1)


def _invalid_ref_reason(ref: str) -> str:
    if not ref:
        return "Spotless ratcheting requires an explicit base reference."
    if SAFE_RATCHET_REF.fullmatch(ref) is None or any(part in ref for part in FORBIDDEN_REF_PARTS):
        return "Spotless ratchet reference contains unsupported characters."
    return ""


def _is_shallow_checkout(root: Path) -> bool:
    completed = _git_probe(root, "rev-parse", "--is-shallow-repository")
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _probe_ref(root: Path, ref: str) -> tuple[bool, bool]:
    available = (
        _git_probe(
            root,
            "rev-parse",
            "--verify",
            "--quiet",
            "--end-of-options",
            f"{ref}^{{commit}}",
        ).returncode
        == 0
    )
    return available, not available and _is_shallow_checkout(root)


def _git_probe(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603
        ("git", *args),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
