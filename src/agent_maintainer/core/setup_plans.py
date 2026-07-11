"""Side-effect-free setup target selection and preview rendering."""

from pathlib import Path


def selected_root(target: Path | None, *, discovered: Path) -> Path:
    """Return an explicit repository root or the discovered current project."""

    return discovered if target is None else target.resolve()


def print_bootstrap_plan(
    repo_root: Path,
    dependency_file: Path,
    *,
    local_source: bool,
) -> None:
    """Print dependency-only bootstrap actions."""

    virtualenv = repo_root / ".venv"
    print(f"would ensure virtualenv: {virtualenv}")
    print(f"would install dependencies from: {dependency_file}")
    if local_source:
        print(f"would install editable package: {repo_root}")
    print("hooks are not installed by bootstrap; run `agent-maintainer install` explicitly")


def preview_pre_commit(repo_root: Path) -> int:
    """Print the pre-commit integration action without executing it."""

    if (repo_root / ".pre-commit-config.yaml").exists():
        print(f"would install pre-commit hook in {repo_root}")
    else:
        print("would skip pre-commit: .pre-commit-config.yaml not present")
    return 0
