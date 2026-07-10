<!-- docsync:object docs.release_checklist.overview -->

# Release Checklist

Use this checklist before tagging or publishing Agent Maintainer. It is release
discipline, not the normal local edit loop.

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
- [ ] Pre-release stabilization phases are complete or explicitly deferred in
  `docs/ROADMAP.md`.
- [ ] PyPI project name availability is rechecked immediately before first
  publish: `https://pypi.org/project/agent-maintainer/`.
- [ ] PyPI Trusted Publisher is configured with project name
  `agent-maintainer`, owner `douglasmonsky`, repository `agent-maintainer`,
  workflow `publish.yml`, and environment `pypi`.
- [ ] GitHub `pypi` environment requires manual reviewer approval before
  publishing to the real PyPI project.
- [ ] TestPyPI Trusted Publisher is configured with project name
  `agent-maintainer`, owner `douglasmonsky`, repository `agent-maintainer`,
  workflow `publish.yml`, and environment `testpypi`.

## Versioning

- [ ] `pyproject.toml` has the intended version.
- [ ] `CHANGELOG.md` has an entry for the version being published.
- [ ] Changelog summarizes stabilization work since the previous beta, including
  known limitations.
- [ ] `config/dev-dependencies.txt` and `config/dev-lock.txt` are in sync.
- [ ] If files under `docs/assets/graphics/` changed, confirm the README still
  renders the static image assets clearly.
- [ ] Release tag is annotated:
  `git tag -a vX.Y.Z -m "Agent Maintainer X.Y.Z"`.
- [ ] No generated metadata such as `dist/`, `build/`, `*.egg-info`, or
  `__pycache__/` is staged.

## Required Verification

Run the normal project gates first:

```bash
just doctor
just verify-precommit
just verify
just verify-ci
just verify-security
just verify-manual
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

Release tests intentionally build wheel and sdist artifacts in a temporary
directory, run `twine check`, install each declared extra in clean virtual
environments without `--no-deps`, smoke console scripts from built artifacts,
and check release-state drift such as version/changelog alignment, public
metadata URLs, Trusted Publisher environment names, and existing release evidence
when present.

The `publish` workflow does not trust these local runs as publish authorization.
Its `release-evidence` job reruns full, CI, security, manual, and release checks
from one clean checkout, embeds all five manifests in an exact-commit aggregate,
and gives the aggregate a maximum 24-hour lifetime. Every downstream build,
attachment, TestPyPI, and PyPI job validates that aggregate against its own
clean checkout before acting. Every remote workflow action is pinned to a full
commit SHA with updater metadata, and strict workflow validation covers verify,
deep-verify, and publish. Superseded validation runs may cancel, while deep
verification and publishing runs are non-canceling.

## Publishing

- [ ] Build artifacts from a clean tree.
- [ ] Run `publish` workflow manually with target `testpypi`.
- [ ] Confirm the `release-evidence-<commit>` artifact contains full, CI,
  security, manual, and release manifests for the workflow SHA.
- [ ] Confirm the build job and selected publish job both report
  `release evidence valid` before building or publishing.
- [ ] Confirm Actionlint, workflow schema validation, and strict Zizmor pass for
  `verify.yml`, `deep-verify.yml`, and `publish.yml`.
- [ ] Install from TestPyPI in a clean environment.
- [ ] Run `agent-maintainer --help`.
- [ ] Run `archguard --help`.
- [ ] Run `agent-maintainer init --track core --target <tmp-repo>`.
- [ ] If TestPyPI smoke passes, push the annotated tag, create the GitHub
  release from that tag, and publish the same version to PyPI.
- [ ] Confirm the `publish` workflow completed the `pypi` environment job.
- [ ] Confirm the GitHub release has attached wheel and sdist assets.

## Release Notes

- [ ] Summarize user-facing changes since previous tag or initial beta
  baseline.
- [ ] State any breaking CLI, config, environment variable, or generated-file
  changes.
- [ ] Include verification evidence, including release-only packaging command.
- [ ] List known risks and current beta limitations.
- [ ] Confirm agent-facing hook output stays quiet on success and bounded on
  failure, with full detail routed to `.verify-logs` and uploaded artifacts.
- [ ] Mention Semgrep is excluded from `manual` and `all` extras on Python
  3.13+ while resolver compatibility is unstable there, if still true.

## Smoke Test

- [ ] Install built wheel in a clean virtual environment.
- [ ] Run `agent-maintainer --help`.
- [ ] Run `archguard --help`.
- [ ] Run `agent-maintainer init --track core --target <tmp-repo>`.
- [ ] Merge generated config into a minimal downstream `pyproject.toml`.
- [ ] Run `agent-maintainer verify --profile precommit` in that
  downstream repository.

## Rollback

Package publication cannot be rewritten on PyPI. If a bad beta is published,
release a patched version rather than deleting or replacing the artifact.
<!-- docsync:object.end docs.release_checklist.overview -->
