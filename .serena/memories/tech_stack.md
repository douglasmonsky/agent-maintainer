# Technology Stack

- Python package, `requires-python >=3.11`, CI compatibility matrix 3.11–3.14 on Ubuntu.
- Build backend: `setuptools.build_meta`; packages discovered under `src/`; wheel and sdist are release artifacts.
- Runtime dependency is PyYAML. Optional extras group quality/security tooling (`core`, `agent`, `hardening`, `manual`, `compression`, `mcp`, `all`).
- Three installed console scripts: `agent-maintainer`, `archguard`, and `docsync`.
- Canonical local orchestration is `just`; recipes export `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=src`.
- Python quality stack includes pytest/pytest-cov, Ruff, Pyright, Tach, coverage/diff-cover, Pylint, Radon/Xenon, deptry, vulture, Bandit, pip-audit, Mutmut, Semgrep, Interrogate, and wemake-python-styleguide.
- Node 22 or newer is development-only for repository hygiene: pinned `@taplo/cli` and `markdownlint-cli2`; no application runtime or npm scripts.
- GitHub Actions validate compatibility, deep verification, and publication. Workflow actions are full-SHA pinned and cross-job release artifacts are digest-verified.
- Developer dependencies are declared in `config/dev-dependencies.txt` and pinned in `config/dev-lock.txt`; package metadata and optional extras remain authoritative in `pyproject.toml`.
