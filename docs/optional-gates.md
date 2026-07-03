<!-- docsync:object docs.optional_gates.overview -->
# Optional Gates

Agent Maintainer distinguishes starter adoption from optional hardening. A repo
should enable optional gates because they are relevant, not because the tool can
run them.

## Core

The `core` extra is the minimum useful maintenance loop:

- Ruff;
- Pyright;
- pytest, coverage, pytest-cov, diff-cover;
- Radon and Xenon;
- Pylint;
- deptry;
- vulture;
- Bandit;
- pre-commit.

## Agent

The `agent` track adds generated agent guidance and managed hook files. Hook
execution is configured-repo-only: globally installed hooks no-op unless the
target repo has `[tool.agent_maintainer]`.

## Hardening

Hardening covers docs/config and security-adjacent surfaces:

- pip-audit;
- Gitleaks when secret scanning is enabled;
- actionlint and zizmor for GitHub Actions;
- yamllint;
- check-jsonschema;
- markdownlint-cli2 and Taplo through Node metadata when selected.

## Manual

Manual gates are intentionally slower or more specialized:

- Mutmut;
- Semgrep;
- CycloneDX Python SBOM;
- pip-licenses;
- OSV Scanner or Trivy when the repository shape justifies them.

Manual gates should usually run before PR merge or release, not after every
small edit. If a manual gate becomes stable and high-value for a repo, ratchet
it gradually and document why.

## Skip Statuses

Verifier manifests use specific skipped statuses so agents and humans can tell
why a gate did not run:

- `skipped-disabled`: disabled by configuration or default policy.
- `skipped-missing-optional`: optional config, files, or integration surface is
  absent.
- `skipped-not-applicable`: enabled check found no matching files.
- `skipped-unsafe-config`: configuration would inspect the wrong environment or
  otherwise run unsafely.
- `skipped-required`: normally expected check skipped because explicit repo
  policy disabled its prerequisite.

These statuses are advisory on passing runs unless `--fail-on-optional-skip` is
used. Required paths and required executables still fail normally.

## Generated Guidance

`AGENTS.agent-maintainer.md` lists active gates only. Disabled optional gates are
omitted to reduce agent context. Full gate inventories belong here, in
`pyproject.toml`, and in the verification catalog.

See also:

- [Agent Maintainer guidance](agent-maintainer-guidance.md)
- [Mutation testing](mutation-testing.md)
- [Release checklist](release-checklist.md)
<!-- docsync:object.end docs.optional_gates.overview -->
