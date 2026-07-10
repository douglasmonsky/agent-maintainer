"""Repository-wide validation for local Markdown link targets."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT_BASED_MARKDOWN = frozenset(
    (REPO_ROOT / "docs" / "assets" / "graphics" / "README_SNIPPET.md",)
)
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^\s)]+)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(?P<target><[^>]+>|\S+)", re.MULTILINE)
HTML_LINK = re.compile(r"\b(?:href|src)=[\"'](?P<target>[^\"']+)[\"']", re.IGNORECASE)
FENCED_BLOCK = re.compile(r"^(```|~~~).*?^\1\s*$", re.MULTILINE | re.DOTALL)
IGNORED_SCHEMES = frozenset(("data", "http", "https", "mailto", "tel"))


def markdown_paths() -> tuple[Path, ...]:
    """Return tracked and intentional untracked Markdown files."""

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "*.md",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(REPO_ROOT / path for path in sorted(set(result.stdout.splitlines())))


def local_targets(text: str) -> tuple[str, ...]:
    """Extract local inline, reference-definition, and HTML targets."""

    searchable = FENCED_BLOCK.sub("", text)
    matches = (
        *INLINE_LINK.finditer(searchable),
        *REFERENCE_LINK.finditer(searchable),
        *HTML_LINK.finditer(searchable),
    )
    return tuple(
        target
        for match in matches
        if (target := normalized_local_target(match.group("target"))) is not None
    )


def normalized_local_target(raw_target: str) -> str | None:
    """Return one decoded local path without query or fragment."""

    target = raw_target.removeprefix("<").removesuffix(">")
    if not target or target.startswith(("#", "//")):
        return None
    parsed = urlsplit(target)
    if parsed.scheme.lower() in IGNORED_SCHEMES:
        return None
    if parsed.scheme or not parsed.path:
        return None
    return unquote(parsed.path)


def resolved_target(source: Path, target: str) -> Path:
    """Resolve a repository-root or document-relative local target."""

    if target.startswith("/"):
        return REPO_ROOT / target.lstrip("/")
    base = REPO_ROOT if source in REPO_ROOT_BASED_MARKDOWN else source.parent
    return base / target


def test_all_repository_local_markdown_links_resolve() -> None:
    """Every checked-in local Markdown target exists."""

    broken = [
        f"{source.relative_to(REPO_ROOT)} -> {target}"
        for source in markdown_paths()
        for target in local_targets(source.read_text(encoding="utf-8"))
        if not resolved_target(source, target).exists()
    ]

    assert broken == []
