+++
id = "static-html-report"
kind = "feature"
status = "active"
base_ref = "origin/main"
expires = 2026-07-13
allowed_paths = [
  ".agent-maintainer/change-plans/**",
  "README.md",
  "docs/**",
  "src/agent_maintainer/cli.py",
  "src/agent_maintainer/report/**",
  "tach.toml",
  "tests/report/**",
]
forbidden_paths = ["config/prod/**", ".env", ".env.*"]
max_changed_files = 25
max_changed_lines = 2000
allow_source_without_test_change = false
requires_tests = true
requires_full_verify = true
ratchet_targets = []
+++

# Cohesive Change Plan: Static HTML Report

## Why this change intentionally large

Phase 34 adds one cohesive report surface: `agent-maintainer report html`.
The feature needs a CLI adapter, report renderer modules, report tests,
documentation, and Tach domain declarations in one branch so the static report
is usable and architecturally assigned when it lands.

## Why this should not be split smaller

Splitting the command from the renderer would create a dead CLI or unreachable
package. Splitting the renderer from Tach/docs would leave a new subpackage
without the strict architecture coverage this repository requires. The work is
still bounded to one downstream presentation layer that only consumes existing
verification artifacts.

## What allowed to change

Allowed changes are the `agent_maintainer.report` package, top-level CLI
dispatch to that package, report-specific tests, README/tool-map documentation,
the report package Tach domain, the root Tach entry for changed CLI imports,
and the required architecture decision note.

## What must not change

Do not change verifier execution behavior, scanner policy, profile membership,
release publishing behavior, dependency pins, hook installation behavior, or
diagnostic artifact schemas outside the report reader's existing inputs.

## Verification plan

Run focused report tests and static checks first:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/report/test_html_report.py -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m archguard tach-config --strict-root-module
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/tach check --exact
```

Then run the repository gates:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile precommit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile full
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile ci --base-ref origin/main --compare-branch origin/main
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile security
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer verify --profile manual
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer guidance --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m agent_maintainer doctor --strict
```

## Rollback plan

Revert the static report commits. Existing verifier profiles, artifacts, hooks,
and CI continue to work without the static HTML report because the report
package is downstream of verification.

## Follow-up ratchet work

No ratchet debt is intentionally introduced. If the new report package reveals
larger documentation or renderer thresholds later, handle those in a separate
roadmap phase rather than expanding this branch.
