"""Property tests for cohesive change-plan scope policy."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from agent_maintainer.change_plan import git_scope, parser
from agent_maintainer.change_plan.models import ChangedPath
from tests.change_plan.test_parser import valid_plan_text

COMPONENT_RE = r"[A-Za-z0-9_][A-Za-z0-9_-]{0,16}"
MAX_SCOPE_EXAMPLES = 60
PLAN_PATH = Path("plan.md")


def path_components() -> st.SearchStrategy[list[str]]:
    """Return safe relative path components."""
    return st.lists(
        st.from_regex(COMPONENT_RE, fullmatch=True),
        min_size=1,
        max_size=4,
        unique=False,
    )


def relative_python_paths(prefix: str) -> st.SearchStrategy[str]:
    """Return relative Python paths under prefix."""
    return path_components().map(lambda parts: python_path(prefix, parts))


def python_path(prefix: str, parts: list[str]) -> str:
    """Return a slash-separated Python path."""
    filename = ".".join((parts[-1], "py"))
    return "/".join((prefix, *parts[:-1], filename))


@given(path=relative_python_paths("src"))
@settings(max_examples=MAX_SCOPE_EXAMPLES)
def test_allowed_src_glob_accepts_src_paths(
    path: str,
) -> None:
    """Allowed source glob should not report outside-scope errors."""
    plan = parser.parse_plan_text(valid_plan_text(), path=PLAN_PATH)

    issues = git_scope.path_issues(plan, ChangedPath(path=path, added=1, deleted=0))

    assert not any("outside allowed scope" in issue.message for issue in issues)


@given(path=relative_python_paths("src"))
@settings(max_examples=MAX_SCOPE_EXAMPLES)
def test_forbidden_scope_overrides_allowed_scope(
    path: str,
) -> None:
    """Forbidden patterns should win even when allowed patterns also match."""
    text = valid_plan_text().replace(
        'forbidden_paths = ["config/prod/**"]',
        f'forbidden_paths = ["{path}"]',
    )
    plan = parser.parse_plan_text(text, path=PLAN_PATH)

    issues = git_scope.path_issues(plan, ChangedPath(path=path, added=1, deleted=0))

    assert any("forbidden path" in issue.message for issue in issues)


@given(path=relative_python_paths("app"))
@settings(max_examples=MAX_SCOPE_EXAMPLES)
def test_unlisted_globs_reject_paths(
    path: str,
) -> None:
    """Paths outside the allowed glob should report outside-scope errors."""
    plan = parser.parse_plan_text(valid_plan_text(), path=PLAN_PATH)

    issues = git_scope.path_issues(plan, ChangedPath(path=path, added=1, deleted=0))

    assert any("outside allowed scope" in issue.message for issue in issues)


@given(path=relative_python_paths("src"))
@settings(max_examples=MAX_SCOPE_EXAMPLES)
def test_source_only_scope_requires_test_change(
    path: str,
) -> None:
    """Source-only Python changes should trigger the test-change invariant."""
    plan = parser.parse_plan_text(valid_plan_text(), path=PLAN_PATH)
    changes = (ChangedPath(path=path, added=1, deleted=0),)

    issues = git_scope.scope_issues(plan, changes)

    assert any("source changes require a test change" in issue.message for issue in issues)
