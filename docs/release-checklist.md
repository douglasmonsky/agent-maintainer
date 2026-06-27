# Release Checklist

Use this checklist before tagging or publishing Agent Maintainer. It is release
discipline, not a normal local edit loop.

## Repository State

- [ ] Working tree is clean.
- [ ] Current branch is `main` and matches `origin/main`.
- [ ] HEAD SHA is recorded in release notes.
- [ ] Latest GitHub Actions run on `main` passed.
- [ ] `LICENSE` exists and matches the intended MIT license.
- [ ] `pyproject.toml` includes license, authors, classifiers, keywords, and
  project URLs.
- [ ] README links to the license and this release checklist.
- [ ] Repo visibility and GitHub URLs are correct for public release.
- [ ] PyPI project name availability is rechecked immediately before first
  publish: `https://pypi.org/project/agent-maintainer/`.

## Versioning

- [ ] `pyproject.toml` has the intended version.
- [ ] `CHANGELOG.md` has an entry for the version being published.
- [ ] `config/dev-dependencies.txt` and `config/dev-lock.txt` are in sync.
- [ ] No generated metadata such as `dist/`, `build/`, `*.egg-info`, or
  `__pycache__/` is staged.

## Required Verification

Run the normal project gates first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer doctor --strict
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer verify --profile precommit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer verify --profile full
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer verify --profile security
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer verify --profile manual
```

Then run release-only packaging checks:

```bash
just release-check
```

Equivalent raw command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src AGENT_MAINTAINER_RUN_RELEASE_TESTS=1 \
  python3 -m pytest -m release tests/release -q
```

The release tests intentionally build wheel and sdist artifacts in a temporary
directory, run `twine check`, install each declared extra in clean virtual
environments without `--no-deps`, and smoke the console script from built
artifacts.

## Publishing

- [ ] Build artifacts from a clean tree.
- [ ] Publish to TestPyPI first.
- [ ] Install from TestPyPI in a clean environment.
- [ ] Run `agent-maintainer --help`.
- [ ] Run `agent-maintainer init --track core --target <tmp-repo>`.
- [ ] If TestPyPI smoke passes, publish the same version to PyPI.
- [ ] Create a GitHub release/tag after package publication succeeds.

## Release Notes

- [ ] Summarize user-facing changes since the previous tag or initial beta
  baseline.
- [ ] State whether the release has breaking CLI, config, environment variable,
  or generated-file changes.
- [ ] Include verification evidence, including the release-only packaging
  command.
- [ ] List known risks and current beta limitations.

## Smoke Test

- [ ] Install the built wheel in a clean virtual environment.
- [ ] Run `agent-maintainer --help`.
- [ ] Run `agent-maintainer init --track core --target <tmp-repo>`.
- [ ] Merge the generated config into a minimal downstream `pyproject.toml`.
- [ ] Run `python3 -m agent_maintainer verify --profile precommit` in that
  downstream repository.

## Rollback

Package publication cannot be rewritten on PyPI. If a bad beta is published,
release a patched version rather than deleting or replacing the artifact.
