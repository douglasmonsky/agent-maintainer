"""Property tests for safe context file expansion rules."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from agent_context.reading import file_safety

COMPONENT_RE = r"[A-Za-z0-9_][A-Za-z0-9_-]{0,16}"
MAX_PART_EXAMPLES = 80
MAX_NAME_EXAMPLES = 40
MAX_ORDINARY_EXAMPLES = 60


def path_components() -> st.SearchStrategy[list[str]]:
    """Return safe relative path components."""
    return st.lists(
        st.from_regex(COMPONENT_RE, fullmatch=True),
        min_size=0,
        max_size=3,
        unique=False,
    )


def ordinary_components() -> st.SearchStrategy[list[str]]:
    """Return relative components that are not path-level refusals."""
    refused = file_safety.REFUSED_PARTS | file_safety.LOCK_FILE_NAMES
    return st.lists(
        st.from_regex(COMPONENT_RE, fullmatch=True).filter(lambda item: item not in refused),
        min_size=0,
        max_size=3,
        unique=False,
    )


@given(
    prefix=path_components(),
    refused=st.sampled_from(sorted(file_safety.REFUSED_PARTS)),
    suffix=path_components(),
)
@settings(max_examples=MAX_PART_EXAMPLES)
def test_refused_parts_block_context(
    prefix: list[str],
    refused: str,
    suffix: list[str],
) -> None:
    """Generated and cache directory names should always be refused."""
    path = Path(*prefix, refused, *suffix, "source.py")

    assert file_safety.refused_path(path)


@given(prefix=path_components(), name=st.sampled_from(sorted(file_safety.LOCK_FILE_NAMES)))
@settings(max_examples=MAX_NAME_EXAMPLES)
def test_lock_names_block_context(
    prefix: list[str],
    name: str,
) -> None:
    """Known lock files should always be refused regardless of parent path."""
    path = Path(*prefix, name)

    assert file_safety.refused_path(path)


@given(
    prefix=path_components(),
    stem=st.from_regex(COMPONENT_RE, fullmatch=True),
    suffix=st.sampled_from(sorted(file_safety.REFUSED_SUFFIXES)),
)
@settings(max_examples=MAX_NAME_EXAMPLES)
def test_refused_suffixes_block_context(
    prefix: list[str],
    stem: str,
    suffix: str,
) -> None:
    """Binary Python artifacts should always be refused by suffix."""
    path = Path(*prefix, f"{stem}{suffix}")

    assert file_safety.refused_path(path)


@given(
    prefix=ordinary_components(),
    stem=st.from_regex(COMPONENT_RE, fullmatch=True),
)
@settings(max_examples=MAX_ORDINARY_EXAMPLES)
def test_regular_python_paths_reach_content_check(
    prefix: list[str],
    stem: str,
) -> None:
    """Ordinary Python paths should require content inspection, not path denial."""
    path = Path(*prefix, f"{stem}.py")

    assert not file_safety.refused_path(path)
